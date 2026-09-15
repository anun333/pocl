Self-reporting a regression I found in this series while testing it against
narrower kernel-library variants. A default `native` build is unaffected.
`-DKERNELLIB_HOST_CPU_VARIANTS=distro` builds are affected, which is what
distributions ship.

## Symptom

Host: Zen 3 (AVX2, no AVX-512). `distro` build, SSE-class variant selected
via `POCL_KERNELLIB_NAME=sse2`. `sin`/`cos`/`tan` return wrong results at
vector widths above 128 bits (`float8`, `double4`, `double8`); widths that
fit an SSE register are correct. Unpatched `main` is correct at all widths.

## Root cause

**The vector-library call that gets emitted does not depend on the
kernel-library variant.** For this kernel:

```c
__kernel void k(__global const double* i, __global double* o) {
  int x = get_global_id(0);
  double8 v = vload8(x, i);
  vstore8(sin(v), x, o);
}
```

the undefined symbols in the generated `k.so.o` are:

| build | variant | emitted call | correct? |
|---|---|---|---|
| this series | `sse2` | `_ZGVdN4v_sin` | **no** |
| this series | `avx2` | `_ZGVdN4v_sin` | yes |
| unpatched `main` | `sse2` | *(none)* | yes |

Identical symbol for both variants. `_ZGVdN4v_sin` is the **AVX2** 4-wide
double entry point, and per the x86-64 vector ABI it takes its argument in
a 256-bit YMM register.

But the object compiled for the `sse2` variant has no YMM registers at all:

```
$ objdump -d k.so.o | grep -c ymm
0
$ objdump -d k.so.o | grep -c xmm
16
```

So the argument is passed in XMM registers while the callee reads YMM0.
The call does not fault — the host has AVX2, so libmvec's instruction
stream is legal — it simply reads the wrong register. Hence wrong results
rather than a crash.

Unpatched `main` emits no vector-library call for this kernel, which is
why it is correct: it uses the variant's own kernel-library implementation.

Denying the functions at runtime on the same build restores correct results,
confirming the swap is the path:

```
POCL_VECMATH_DENY=sin,sinf,cos,cosf,tan,tanf,llvm.sin.f32,llvm.sin.f64,\
llvm.cos.f32,llvm.cos.f64,llvm.tan.f32,llvm.tan.f64
```

## Where it enters

Bisect at the `sse2` variant, sin/cos/tan, all widths, float and double:

| commit | result |
|---|---|
| unpatched `main` | correct |
| trig fix alone | correct |
| `bd2b5cf23` vector library table in the IR pipeline | correct |
| `c580a5dbb` register the table in `populateModulePM` too | **SIGILL** |
| `e3df253b0` | **SIGILL** |
| `9340e4f9f` AVX-512 rows only on AVX-512 hosts | wrong results |
| series HEAD | wrong results |

The SIGILL at `c580a5dbb` is the same class of bug one ISA level up: that
commit makes the `_ZGVe` (AVX-512) rows reachable, and on a host without
AVX-512 the emitted call really is illegal — exactly as `9340e4f9f`'s
message anticipates. `9340e4f9f` fixes the crash by dropping those rows:

```c
__builtin_cpu_init();
HaveAVX512 = __builtin_cpu_supports("avx512f");
```

> The CPU device compiles for the host, so ask the host.

That assumption holds for a `native` build. It does not hold for a
`distro` build, where the selected variant can be narrower than the host.
With the AVX-512 rows gone, the vectorizer falls to the AVX2 rows — which
the host supports and the SSE2 variant cannot satisfy.

**The submitted state does not crash.** I verified HEAD and unpatched
`main` both run cleanly with an AVX-512 variant forced on this host. The
SIGILL is confined to intermediate commits, so the series is not
bisect-clean, but its final state is crash-free.

## Suggested direction

`9340e4f9f` already has the right mechanism and asks the wrong question.
Filtering rows against the **target kernel-library variant's** feature
level rather than the host's — and extending the same ladder one rung down,
so `_ZGVd` is dropped for SSE-class variants exactly as `_ZGVe` is dropped
today — would cover both cases with one rule. That is contained to the same
function, so it belongs in this PR rather than a follow-up.

Marked draft so it is not sitting in the review queue while this is open.

Measured with an independent ULP harness (PyOpenCL driving real kernels,
mpmath references), glibc 2.39 / LLVM 22 / znver3. Happy to share it or cut
a smaller standalone reproducer.
