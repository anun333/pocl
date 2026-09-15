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
