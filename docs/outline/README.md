# Structural outline — sketch and estimates

**Status: sketch.** Nothing below is written yet except this file. Drafted
2026-09-16 while the CTS run holds the CPU, so the estimates assume
writing-only work with no builds or benchmarks.

## What this is for

The intent, in Seth's words: *a full structural outline of the math and
logic of these repos, versioned.*

The reason it exists: on 2026-09-12 everything under `~/dev` was wiped.
Code came back, because GitHub keeps a PR's commits reachable. **Reasoning
did not** — it survived only where it had been written into prose, in
memory notes and commit messages. Everything reconstructed since has come
out of those, not out of the code.

So the target here is not documentation of *what the code does* — the code
says that, and says it more reliably. It is the layer above: why a bound is
2 ULP and not 4, why a function is denied, why a call is emitted at one
width and not another. That layer is what evaporates.

## Two axes

**Math** — the numerical content. True independent of PoCL; would still be
true if this project used a different runtime.

**Machinery** — how PoCL actually gets from OpenCL C to a `.so`, and where
in that path each decision is made. PoCL-specific, and the part that has
repeatedly surprised us.

The distinction matters because almost every bug this project has found sat
at the *seam*: a numerically correct function reached through machinery that
picked the wrong width, the wrong ABI, or the wrong library.

## Proposed structure

```
docs/outline/
  README.md              <- this file
  10-math/
    ulp.md               what ULP means here, why fractional, how measured
    bounds.md            OpenCL's per-function bounds vs glibc's tolerance
    argument-reduction.md  trig range reduction, Payne-Hanek, the lane bug
    hard-cases.md        exp/log1p tails, cbrt's scalar fallback, subnormals
  20-machinery/
    compile-path.md      OpenCL C -> Clang -> IR -> WG function -> codegen
    vector-library.md    the table, its 3 registration sites, swap, deny-list
    variants.md          native vs distro, CU selection, host vs target
    conformance.md       what ENABLE_CONFORMANCE actually gates
  30-deps/               <- connectors, see below
  40-traps.md            things that have cost time more than once
```

## Estimates

Honest driver: how much is already established versus needs fresh work.
"Established" means it was determined this session and verified, so writing
is transcription plus editing.

| doc | state of knowledge | est. |
|---|---|---|
| `10-math/ulp.md` | established (harness implements it) | 45m |
| `10-math/bounds.md` | **partly** — have OpenCL bounds in the harness table and glibc's 4-ULP claim, but have not read the OpenCL spec section itself | 1.5h |
| `10-math/argument-reduction.md` | established for the lane bug; Payne-Hanek itself needs reading | 2h |
| `10-math/hard-cases.md` | established (exp/log1p/cbrt all traced to specific inputs) | 1h |
| `20-machinery/compile-path.md` | **weakest** — traced pieces, never the whole path end to end | 3h |
| `20-machinery/vector-library.md` | established tonight, thoroughly | 1h |
| `20-machinery/variants.md` | established tonight (the regression lived here) | 1h |
| `20-machinery/conformance.md` | partly — know the gating empirically, not exhaustively | 1.5h |
| `40-traps.md` | established, painfully | 45m |
| connectors (6 files) | see below | 4h |

**Total ≈ 17h.** Call it three or four sessions. The single largest item,
`compile-path.md`, is also the one with the least existing knowledge — it is
the piece we have only ever seen in fragments while chasing specific bugs.
Worth doing precisely for that reason, but it should be costed as
investigation, not transcription.

## Connectors to dependency repos

Each connector answers four questions, in this order:

1. **What we depend on** — the specific surface, not the project in general
2. **The interface** — the actual contract, named concretely
3. **What breaks** — failure modes seen, or plausible
4. **Our standing there** — what we have filed, and its state

| connector | the surface we actually touch | est. |
|---|---|---|
| `llvm.md` | `VecFuncs.def` table; `TargetLibraryInfo`/TLII; LoopVectorize width choice; `X86TargetParser::getFeaturesForCPU`; SLP. Filed: [#223817](https://github.com/llvm/llvm-project/pull/223817). Open upstream: [#204678](https://github.com/llvm/llvm-project/issues/204678), [#206273](https://github.com/llvm/llvm-project/issues/206273) | 1h |
| `glibc-libmvec.md` | the `_ZGV<isa><mask><vlen>v_` ABI; IFUNC dispatch; `bits/math-vector.h` declare-simd; documented 4-ULP tolerance; version tags `@@GLIBC_2.22` vs `@@GLIBC_2.35` | 1h |
| `sleef.md` | **two distinct things routinely confused**: the copy vendored at `lib/kernel/sleef/` (plain files, no submodule) and the system `libsleefgnuabi`. Upstream bug worth tracking: [sleef#707](https://github.com/shibatch/sleef/issues/707), SIGILL on x86-64-v2 | 45m |
| `opencl-cts.md` | the acceptance gate; `math_brute_force`; wimpy vs full; build requirements (SPIR-V headers, Khronos headers, `libOpenCL.so` symlink); thread budget | 45m |
| `khronos-headers.md` | why the CTS needs headers newer than the distro ships; the enum surface | 20m |
| `clspv-mesa.md` | the April path, currently dormant; clspv's open crash bugs; Rusticl/RadeonSI | 30m |

## Sequencing

Written in this order, because each supplies vocabulary the next assumes:

1. `40-traps.md` — cheapest, highest immediate value, and purely perishable
2. `20-machinery/vector-library.md` + `variants.md` — freshest, and the
   regression makes them concrete rather than abstract
3. `30-deps/llvm.md` + `glibc-libmvec.md` — the two that most of the above
   leans on
4. `10-math/*` — more stable knowledge, less urgent, ages slowest
5. `20-machinery/compile-path.md` — last, because it is investigation and
   wants the CPU free

## What this is not

Not a replacement for `RECOVERY.md`, which is a chronological record of one
recovery and should stay that way. Not API docs. Not a tutorial —
[`../explainers/`](../explainers/) is the plain-language layer, and already
has the LLVM patch explainer as its first entry. The outline is the
reference layer between them.
