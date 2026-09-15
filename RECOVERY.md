# Recovered from GitHub, 2026-09-15

The `sethc555` GitHub account (and its `pocl-revitalization` / `pocl` fork) is gone,
so the working tree here is empty again. But the 4 patch series that got filed as
real PRs against `pocl/pocl` were still fetchable as PR refs, because a PR keeps
its commits reachable on the *base* repo even after the source fork disappears:

- `pr-2307-pown`    -- CPU kernel library: keep libclc pown when vectorizing builtins
- `pr-2308-api`     -- API fixes hidden by ENABLE_CONFORMANCE=OFF, context device reporting
- `pr-2309-trig`    -- float sin/cos/tan lane cross-talk fix + regression test
- `pr-2311-vecmath` -- 21-commit series: per-function deny-list for vectorized math,
                       library-driven builtin swap, extended x86 libmvec table
                       (verified: full 21 commits present, matches memory notes exactly)

All 4 are closed-unmerged upstream (no maintainer review yet). Design issue #2310
(non-uniform-work-group proposal this series stacks on) is still open, zero comments.

## NOT recoverable
Two branches existed only on the deleted fork, never opened as PRs, so GitHub has
nothing left to fetch:
- `feat/veclib-direct` (65a86e198) -- vector overloads call libmvec directly instead
  of through SLP; A/B-tested 3.4x faster (float) / 2.1x (double) than the PR's approach.
- `fix/no-frexp-swap` (64b798bbf) -- LLVM 23 vector double pown/rootn/powr fix.

Both are described in enough prose detail in
`~/.claude/projects/-home-seth-dev-openpocl/memory/pocl-stage0-status.md`
to redo, just not as diffs -- they'd be rewritten from the description, not restored.

## Environment
`pocl-cpu-dev:llvm22` (+ 2 Mesa variants) Docker images are still on this machine,
untouched. The build/test recipe (`tools/docker/run.sh`, env vars, CPU budget) is
documented in `pocl-workspace-layout.md` in the same memory folder.

## Harness rebuilt, 2026-09-15

Reconstructed `harness/` from the prose in `pocl-stage0-status.md` (original
source was in the lost sidecar repo, never filed as a PR so nothing survived
on GitHub). Python + PyOpenCL, executes real kernels against the built PoCL,
measures ULP error against mpmath high-precision references.

Validated against the just-rebuilt `build-conf-vec-fix` (vecmath PR branch):
**250/250 sweep rows pass** (25 functions x widths 1,2,3,4,8 x float+double)
-- matching the *exact* "harness clean 250 rows" figure from the original
session notes at this point in the project. `scalar_libm.py`'s cbrt reading
(2.90 ULP) also lands almost exactly on the original's "2.88 ULP."

Known gaps vs. the original (not in the notes in enough detail to rebuild,
or out of scope for a first pass):
- multi-output builtins (fract/modf/frexp/remquo/sincos) -- different kernel
  signature, not yet implemented
- `harness/determinism/int_kernels.py` (bit-identical across loopvec/cbs) --
  not rebuilt
- Rusticl/GPU-path testing, SLEEF-specific probes, the `--ftz` device
  detection is implemented but not exercised against a denormal-free device
  here (this build/device supports denormals)

Full results: `results/full-sweep-20260915.json`.

## Trig bug reconfirmation, 2026-09-15 evening — the missing variable was ENABLE_CONFORMANCE

Spent a while trying to reproduce PR #2309's exact cited repro
(`sin((float4)(FLT_MIN, 1e8f, 1, 1)).x` returning `0.0078124` instead of
`FLT_MIN`) against vanilla upstream main, with no luck across several
attempts (literal constants, buffer-sourced inputs, various work-item
counts and work-group sizes). All returned the correct result.

Reread the original session transcript itself (not just the memory
summaries) and found the actual discovery script — it built into a
directory named `build-conf`. **The missing variable was
`-DENABLE_CONFORMANCE=ON`.** Once added:

- Vanilla main + `ENABLE_CONFORMANCE=ON`: reproduces the bug exactly,
  digit-for-digit against the original session output, for every
  large-neighbor test case (FLT_MAX, inf, 1e28, 1e10, 1e8); correctly does
  *not* trigger for NaN or a below-threshold value (200) -- matches the
  original pattern precisely.
- `pr-2311-vecmath` (patched) + `ENABLE_CONFORMANCE=ON`: every case
  returns the correct result.

Lesson for next time: **when trying to reproduce a specific bug from these
notes, check what build variant it was found on first** (`build-conf`,
`build-fast`, `build-fast-sleef`, etc. in the original naming --
documented in `pocl-workspace-layout.md`) rather than assuming default
CMake flags. The exact-value scripts are in `harness/reconfirm.py` and
`harness/reconfirm_trig_exact.py` (the latter is a faithful copy of the
original discovery script, found in the openpocl session transcript at
`~/.claude/projects/-home-seth-dev-openpocl/a7e4392a-....jsonl` line ~1513).

## ISA bisect on the wide-vector bug, 2026-09-15

Ran the harness at each kernel-library variant on `build-patched-distro`
(sin/cos/tan, all widths, both precisions):

| variant | register width | result |
|---|---|---|
| sse2   | 128-bit | 21/30 |
| ssse3  | 128-bit | 21/30 |
| sse41  | 128-bit | 21/30 |
| avx    | 256-bit | **30/30** |
| avx2   | 256-bit | **30/30** |

Clean boundary: **the whole 128-bit SSE family fails identically; both
256-bit AVX variants pass.** So this is not an SSE2-specific bug, as first
assumed — it tracks native register width exactly. The failing cases were
float8 and double4/double8, i.e. precisely the OpenCL vector widths that
exceed 128 bits. AVX (256-bit) handles float8/double4 natively and
apparently splits double8 correctly.

Working hypothesis: a kernel-library variant mis-handles OpenCL vector
types wider than its native register width, rather than splitting them.
Still not filed — needs `build-vanilla-distro` to establish whether this
predates the recovered series before it's worth reporting upstream.

## Regression found in our own series, 2026-09-16

The wide-vector failures are **not** pre-existing in PoCL. Isolated:

| build @ sse2 variant | sin/cos/tan result |
|---|---|
| vanilla upstream main | **30/30 pass** |
| trig fix alone (`pr-2309-trig`) | **30/30 pass** |
| full vecmath series (`pr-2311-vecmath`) | **21/30** — fails float8, double4, double8 |
| vecmath series + `POCL_VECMATH_DENY` for trig | **30/30 pass** |

So: the trig fix is exonerated, and the mechanism is the **vecmath builtin
swap**. Disabling the swap at runtime restores correct results.

**Hypothesis (fits the evidence, not yet proven at source level):** the
vector-library table and swap decisions are filtered on **host CPU
features**, not on the ISA of the kernel-library variant being compiled.
The series' own commits do host-based filtering explicitly — e.g. "add
AVX-512 libmvec rows only on hosts with AVX-512", and "on a host without
AVX-512 every _ZGVe row is removed from the merged table". On an AVX2 host
running an SSE2 kernel-library variant, the AVX2 rows (`_ZGVdN4v_*`,
4-wide double / 8-wide float) stay in the table, and SSE2-targeted kernel
code can reach them — a width/ISA mismatch that yields garbage.

**Scope, stated honestly:** this needs variant ISA ≠ host capability. A
default `native` build has variant == host, which is why every earlier
native-build run passed 250/250. The realistic trigger is the supported
`POCL_KERNELLIB_NAME` override on a `distro`-style multi-variant build. On
genuinely old hardware (a real SSE2-only host) the table would be built
from that host's features, so it would likely not mismatch. Narrow
trigger — but a real regression under a supported configuration, in code
we have asked upstream to review (bundled in pocl/pocl#2320).

**Side finding, pointing the other way:** vanilla PoCL at sse2 *is* broken
for `pown` (760k-2.2e9 ULP at float w1/w3/w4/w8 and double w4), and our
pown fix repairs it. That's independent corroboration for pocl/pocl#2319,
stronger than what its description currently claims.

### Bisect correction: the IR-pipeline commit is not the culprit

I hypothesised the trigger was `bd2b5cf23` ("Vector library table in the IR
pipeline"), reasoning that registering the table for the new-pass-manager
pipeline lets the loop vectorizer choose widths from the table alone,
before codegen knows its CPU. The source reading behind that is still
correct as far as it goes:

- `createFilteredTLII` is built from `Dev->llvm_target_triplet`, and a
  triple encodes architecture, not CPU feature level — PoCL tracks those
  separately (`pocl_get_llvm_cpu_name`, `pocl_get_distro_kernellib_variant`).
- The existing row filter asks `hostHasAVX512()` (`__builtin_cpu_supports`)
  — the **host**, not the kernel-library variant being compiled — and
  there is no equivalent filter one rung down for `_ZGVd` (AVX2) rows when
  the target variant is SSE2-class.

**But the bisect refutes it as the trigger:** both `d6d1d11ee` (the commit
before) and `bd2b5cf23` itself pass 30/30 at the sse2 variant. The extended
table (`340de12f6`) is already present at that point too. So the
triple-vs-variant gap exists there and does *not* fire.

Something later in the series makes the table richer or reach further.
Next suspects: `c580a5dbb` (registers the table in `populateModulePM` as
well — a third registration site) and `2c1c22d1e` (rebuilds the merged
table, and is where the host-based `_ZGVe` filtering lands).

Recording this because the mechanism story was stated more confidently
than the evidence supported. The mechanism may still be the *explanation*;
it is not yet the identified *cause*.

### Bisect, completed — and a second correction

Two things I got wrong before reaching the real picture, both recorded
above: the IR-pipeline commit was refuted as the trigger, and my grep for
`^sweep ` silently read **crashes as no-result**. Commits 12-13 do not
pass; they die with SIGILL (exit 132, core dumped).

Full bisect at the `sse2` variant on an AVX2 (Zen 3, no AVX-512) host:

| # | commit | result |
|---|---|---|
| — | vanilla upstream main | 30/30 pass |
| 1-2 | trig fix alone | 30/30 pass |
| 10 | `bd2b5cf23` IR pipeline | 30/30 pass |
| 12 | `c580a5dbb` register in populateModulePM too | **SIGILL** |
| 13 | `e3df253b0` deny float cbrt | **SIGILL** |
| 14 | `9340e4f9f` AVX-512 rows only on AVX-512 hosts | 21/30 (crash fixed, wrong results remain) |
| 21 | series HEAD (= what #2320 contains) | 21/30 |

**The story that fits all of it:**

1. The extended table (`340de12f6`) adds `_ZGVe` (AVX-512) rows. Harmless
   at first — nothing reaches them.
2. `c580a5dbb` registers the table in a third place (`populateModulePM`),
   making those rows reachable by the vectorizer. On a host without
   AVX-512 the emitted call is AVX-512 code → **SIGILL**.
3. `9340e4f9f` fixes the crash by dropping `_ZGVe` rows — but asks
   `__builtin_cpu_supports("avx512f")`, i.e. the **host**. Its own comment
   states the assumption plainly: *"The CPU device compiles for the host,
   so ask the host."*
4. That assumption is false under `KERNELLIB_HOST_CPU_VARIANTS=distro`,
   where the selected variant can be narrower than the host. With the
   crash gone, the vectorizer falls to the next widest rows — `_ZGVd`
   (AVX2, 4x double / 8x float) — which the host supports but the **SSE2
   kernel-library variant** cannot satisfy. Hence wrong results, not a
   crash, at exactly the widths above 128-bit.

**State of the submitted PR (#2320 = HEAD): no crash.** Verified: HEAD and
vanilla both exit 0 with an AVX-512 variant forced on this host. The defect
in the submitted state is wrong results for sin/cos/tan at float8 /
double4 / double8 when an SSE-class variant is selected. The SIGILL is an
intermediate-commit artifact — the series is not bisect-clean, but its
final state does not crash.

**Fix shape:** `9340e4f9f` already has the right mechanism; it asks the
wrong question. Filter rows against the **target kernel-library variant's**
feature level rather than the host's, and extend the ladder one rung down
so `_ZGVd` is dropped for SSE-class variants, exactly as `_ZGVe` is
dropped today. Contained to the same function — belongs inside #2320, not
a separate PR.
