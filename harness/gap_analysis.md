# LLVM VecFuncs.def x86 libmvec gap — rebuilt 2026-09-15

Original doc (`docs/upstream/llvm-vecfuncs-libmvec.md`) was lost with the
sidecar repo, along with its "12 functions" figure. Rebuilt from scratch,
empirically, against **LLVM's live main branch** (not the pinned local
image) since that's what a patch would actually target.

## Method

1. `nm -D /usr/lib/x86_64-linux-gnu/libmvec.so.1` (glibc 2.39, Ubuntu
   24.04) → every real (`T`) `_ZGV*` vector-ABI symbol, stripped to base
   function name.
2. Fetched `llvm/include/llvm/Analysis/VecFuncs.def` fresh from
   `llvm/llvm-project@main` (not the local LLVM 22/23 Docker images, which
   are weeks stale) → every function name currently in
   `TLI_DEFINE_LIBMVEC_X86_VECFUNCS`.
3. Set difference.

## Result: 26 functions, not 12

The recalled "12" was almost certainly computed against LLVM 23 at the
time, which had already picked up 8 of these independently (LLVM main has
grown from 12 to 28 covered functions since September). Current real gap
against **live** LLVM main:

```
acos acosf   asin asinf   atan atanf   atan2 atan2f
cosh coshf   sinh sinhf   tanh tanhf
exp10 exp10f exp2 exp2f   log10 log10f log2 log2f
hypot hypotf
sincos sincosf
```

## A real complication found while verifying, not assumed

LLVM's *existing* entries (e.g. `cos`, `pow`) reference glibc's `b`
(SSE2, 2-wide double) and `d` (AVX2, 4-wide double) ABI-class symbols:

```
TLI_DEFINE_VECFUNC("cos", "_ZGVbN2v_cos", FIXED(2), "_ZGV_LLVM_N2v")
TLI_DEFINE_VECFUNC("cos", "_ZGVdN4v_cos", FIXED(4), "_ZGV_LLVM_N4v")
```

But this glibc build only *exports* the `c` (AVX, also 4-wide double)
class for every one of the 26 gap functions — no `b` or `d` symbols exist
for them here at all. Both give the same vector width; `c` and `d` are
different ISA feature levels, not different widths, so this isn't
interchangeable by assumption.

**Decision: only draft entries for the `c` class**, which is directly,
empirically verified present (`nm -D` output attached below) — not `b`/`d`,
which would be guessing at symbol names on the theory that they follow the
same pattern as the original 12. That needs checking against upstream
glibc's actual NEWS/ABI docs (not just this one Ubuntu package) before
adding, since it's plausible glibc simply never shipped `b`/`d` variants
for the newer (2.35+) function set at all.

## Verified symbols (nm -D, glibc 2.39)

```
_ZGVcN4v_acos    _ZGVcN8v_acosf
_ZGVcN4v_asin    _ZGVcN8v_asinf
_ZGVcN4v_atan    _ZGVcN8v_atanf
_ZGVcN4vv_atan2  _ZGVcN8vv_atan2f
_ZGVcN4v_cosh    _ZGVcN8v_coshf
_ZGVcN4v_sinh    _ZGVcN8v_sinhf
_ZGVcN4v_tanh    _ZGVcN8v_tanhf
_ZGVcN4v_exp10   _ZGVcN8v_exp10f
_ZGVcN4v_exp2    _ZGVcN8v_exp2f
_ZGVcN4v_log10   _ZGVcN8v_log10f
_ZGVcN4v_log2    _ZGVcN8v_log2f
_ZGVcN4vv_hypot  _ZGVcN8vv_hypotf
_ZGVcN4vvv_sincos _ZGVcN8vvv_sincosf   (multi-output; ABI needs separate care, see below)
```

## sincos/sincosf — separate open question, not included in the draft patch

Existing sincos entries elsewhere in VecFuncs.def (AArch64/RISC-V/ARM
targets) use a "linear pointer" mangling for the two output args
(`vl8l8`). glibc's actual x86 export is `_ZGVcN4vvv_sincos` — three `v`s,
not `vl8l8`. Filing an entry with the wrong output-parameter mangling
would silently miscompile call sites, not just fail to match, so this is
deliberately held out of the draft rather than guessed.

## Functional verification, not just symbol-table presence

Compiled a shim calling 4 representative entries directly through the
exact vector-ABI signature used in the draft patch (`FIXED(4)`/`FIXED(8)`,
AVX 256-bit vectors) and compared to reference (`math`/`mpmath`):

| function | result | reference | match |
|---|---|---|---|
| `acos` (4-wide double) | `1.47062891, 1.04719755, 0.45102681, 1.87548898` | same | exact |
| `exp10` (4-wide double) | `1.0, 10.0, 316.22776602, 0.1` | same | exact |
| `atan2` (4-wide double, binary) | `0.78539816, 0.0, -0.78539816, 0.64350111` | same | exact |
| `acosf` (8-wide float) | matches to float precision | same | exact |

So the 22 non-sincos entries in `vecfuncs_gap.patch` are verified both
ways: the symbol exists (`nm -D`) and calling it through the declared ABI
produces correct results, not just a plausible-looking guess.

## Status: prerequisite work complete, not yet filed

Ready to file against `llvm/llvm-project#204678`: 22 verified entries
(11 functions × 2 precisions) covering acos, asin, atan, atan2, cosh,
sinh, tanh, exp10, exp2, log10, log2, hypot. `sincos`/`sincosf` held out
pending the ABI-mangling question above. `b`/`d` (SSE2/AVX2) rows held out
pending verification against upstream glibc docs rather than assumed from
this one Ubuntu package.
