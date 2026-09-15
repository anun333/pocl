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
