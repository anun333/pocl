# LLVM VecFuncs.def x86 libmvec gap — rebuilt 2026-09-15

Original doc (`docs/upstream/llvm-vecfuncs-libmvec.md`) was lost with the
sidecar repo, along with its "12 functions" figure. Rebuilt from scratch,
empirically, against **LLVM's live main branch** (not the pinned local
image) since that's what a patch would actually target.

## Method

1. `nm -D /usr/lib/x86_64-linux-gnu/libmvec.so.1` (glibc 2.39, Ubuntu
   24.04) → every `_ZGV*` vector-ABI symbol, stripped to base name.
   **Include IFUNC (`i`) symbols, not just `T`** — see the correction below.
2. Fetched `llvm/include/llvm/Analysis/VecFuncs.def` fresh from
   `llvm/llvm-project@main` (not the local LLVM 22/23 Docker images, which
   are weeks stale) → every function name currently in
   `TLI_DEFINE_LIBMVEC_X86_VECFUNCS`.
3. Set difference.

## Correction: a wrong turn worth recording

A first pass filtered `nm` output to `T` symbols only and concluded that
this glibc exports **only** the `c` (AVX) ABI class for the gap functions,
and that `b`/`d` rows therefore couldn't be written without guessing. A
draft patch was written on that basis. **That was wrong.**

glibc dispatches `b`, `d` and `e` through GNU IFUNC, so they carry symbol
type `i`, not `T`. The `T`-only filter saw 54 symbols; the real count is
**216 = 54 functions × 4 ABI classes**, perfectly symmetric:

```
54 _ZGVbN   (SSE2, 128-bit)
54 _ZGVcN   (AVX,  256-bit)
54 _ZGVdN   (AVX2, 256-bit)
54 _ZGVeN   (AVX-512, 512-bit)
```

Symbol versions also confirm the framing precisely: the original set is
tagged `@@GLIBC_2.22`, the newer additions `@@GLIBC_2.35`.

## Result: 26 functions missing, 24 of them addressable

The recalled "12" was likely computed against LLVM 23 at the time, which
had already picked up 8 independently — LLVM main has grown from 12 to 28
covered functions since September. Current real gap against live main:

```
acos acosf   asin asinf   atan atanf   atan2 atan2f
cosh coshf   sinh sinhf   tanh tanhf
exp10 exp10f exp2 exp2f   log10 log10f log2 log2f
hypot hypotf
sincos sincosf        <- held out, see below
```

## ABI classes: match LLVM's existing convention, b and d only

LLVM's table lists **only `b` (SSE2) and `d` (AVX2)** — `c` and `e` appear
nowhere in the x86 libmvec section. The patch follows that convention
rather than adding all four:

```
TLI_DEFINE_VECFUNC("exp", "_ZGVbN2v_exp", FIXED(2), "_ZGV_LLVM_N2v")
TLI_DEFINE_VECFUNC("exp", "_ZGVdN4v_exp", FIXED(4), "_ZGV_LLVM_N4v")
TLI_DEFINE_VECFUNC("expf", "_ZGVbN4v_expf", FIXED(4), "_ZGV_LLVM_N4v")
TLI_DEFINE_VECFUNC("expf", "_ZGVdN8v_expf", FIXED(8), "_ZGV_LLVM_N8v")
```

All 48 required symbols (12 functions × 2 precisions × 2 classes) verified
present in glibc 2.39. Zero missing.

## sincos/sincosf — held out, with a precise reason

glibc's `bits/math-vector.h` annotates sincos with plain
`_Pragma("omp declare simd notinbranch")`, identical to every other
function — no linear-pointer clause. So the two output pointers of
`void sincos(double, double*, double*)` are vectorised as **vectors of
pointers**, which is why the exported symbol is `_ZGVdN4vvv_sincos`
(three `v`s).

Every other sincos entry in VecFuncs.def (AArch64/RISC-V/ARM) uses the
`vl8l8` form — a base pointer with an 8-byte linear stride — which is the
shape LLVM's vectorizer can actually emit for consecutive memory outputs.
A `vvv` entry would require materialising a vector of pointers, so it would
most likely never match anything the vectorizer produces. Held out
deliberately; this needs a vectorizer-side answer, not a table row.

## Functional verification — both ABI classes, not just symbol presence

Compiled shims calling the declared ABI directly and compared to reference:

| entry | class | result | match |
|---|---|---|---|
| `acos` 2-wide double | b (SSE2) | `1.3181160717, 2.4188584058` | exact |
| `log2` 4-wide double | d (AVX2) | `0.0, 3.0, 10.0, -1.0` | exact |
| `hypot` 2-wide double, binary | b (SSE2) | `5.0, 13.0` | exact |
| `tanhf` 4-wide float | b (SSE2) | `0.0, 0.462117, 0.761594, -0.964028` | exact |
| `atan2f` 8-wide float, binary | d (AVX2) | all 8 lanes | exact |

Unary and binary, both precisions, both ABI classes, all exact against
`math` reference.

## Status: ready to file

`vecfuncs_gap.patch` holds **48 entries** (12 functions × 2 precisions ×
2 ABI classes) for `llvm/llvm-project#204678`: acos, asin, atan, atan2,
cosh, sinh, tanh, exp10, exp2, log10, log2, hypot. sincos/sincosf
excluded for the reason above.

Not yet filed.
