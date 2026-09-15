# PoCL Revitalization

Prove that [PoCL](https://github.com/pocl/pocl) (Portable Computing Language,
an open OpenCL implementation) is a real, fully-open compute path for
hardware the proprietary vendor stacks have abandoned — starting with cheap,
old AMD GPUs (MI25/MI50: ROCm no longer supports them) and, by extension,
any aging x86-64 fleet. The constraint that shaped every pivot below: **$0
hardware, all software** — the fix has to be upstream and open, not a
workaround that only helps one machine.

## Intent, in order

**April 2026 — clspv/AMD attempt** (`~/dev/pocl`, [its own README](../pocl/README.md)).
Started by rewriting llama.cpp's OpenCL kernels to dodge clspv bugs, targeting
PoCL → clspv → SPIR-V → Mesa RADV on the MI25/MI50. Landed "103/103 kernels
compile" — then found that number meant nothing: compiling clspv output
isn't the same as correct inference. 2026-04-13, explicitly ruled out the
easy exit (swap to llama.cpp's native Vulkan backend) because that would
abandon the actual thesis, and recommitted to fixing clspv itself. That
session's transcript aged out of Claude Code's retention window before this
repo was rebuilt; its memory notes are what this paragraph is reconstructed
from.

**September 2026 — clean restart** (this repo, then renamed `openpocl` →
`pocl-revitalization`, GitHub `sethc555/pocl-revitalization`, private). Picked
a narrower, more tractable front: no clspv, no Vulkan — direct upstream
contributions to `pocl/pocl`'s CPU vector-math correctness. Filed four patch
series plus one design issue. Full OpenCL CTS ran clean (159/161; the 2
failures were denied in the same series). Paused cleanly 2026-09-06 at
"let's pause and shut down — save progress," not abandoned mid-work.

**2026-09-12 — everything local and the GitHub account gone.** Part of a
broader pattern, not specific to this project — see the top-level `~/dev`
archive notes. `sethc555` no longer resolves on GitHub at all.

**2026-09-15 — recovered.** GitHub keeps a PR's commits reachable on the
*base* repo even after the source fork is deleted, so all four filed patch
series were still fetchable. Two branches that were pushed to the fork but
never opened as PRs (`feat/veclib-direct`, `fix/no-frexp-swap`) were not —
nothing to fetch without a surviving ref. Forked fresh under `anun333`,
rebuilt the ULP-sweep harness from the session notes (source was in this
repo, which was lost), and validated the recovered vecmath branch: **250/250
harness rows pass** — matching the exact figure the original notes report at
this point in the project.

## Current state (2026-09-15)

- Fork: `github.com/anun333/pocl` — branches `pr-2307-pown`, `pr-2308-api`,
  `pr-2309-trig`, `pr-2311-vecmath` (all recovered in full), `sidecar-docs`
  (this repo's content).
- All four original PRs show as **closed-unmerged** on `pocl/pocl`, closed by
  "ghost" (GitHub's marker for a deleted account) on 2026-09-11 — an
  automatic side effect of `sethc555` being deleted, not a maintainer
  rejection. Nothing about the technical content was judged.
- Design issue **#2310** (non-uniform work-group proposal one branch of this
  work stacks on) is still **open**, zero comments.
- Build verified clean: PoCL's own regression suite 144/144, harness sweep
  250/250 (25 functions × widths 1/2/3/4/8 × float/double) against the
  recovered `pr-2311-vecmath` branch.
- **Not yet re-filed upstream** — holding per Seth's instruction (2026-09-15)
  until the `anun333` identity question is settled.

## Build-improvement opportunities (found 2026-09-15)

1. **SLEEF 3.5.1 → 3.9.0.** The Docker image was built against SLEEF 3.5.1.
   Current release is 3.9.0, and **SLEEF 3.8 (2025-01-27) explicitly fixed
   "oflow bound in log1p(f), exp and pow"** — the exact functions #2311's
   deny-list patches exist to route *around*. Worth a full CTS run against
   3.9.0 before re-filing: the denylist series might shrink, become
   redundant, or (more likely) still be needed for the *libmvec* side even
   if SLEEF's own bug is fixed — but this needs checking, not assuming.
2. **Upstream drift is small.** Only 6 commits ahead of our pin (`f04aac0` →
   `aaaa2d67b` on `main`), including `cmake: add missing section for LLVM 20`
   (#2313). Cheap rebase before re-filing.
3. **Open upstream build-system issues worth knowing about** (not ours,
   but relevant context if touching the build again): CMakeLists.txt
   redundancy between the host-kernel and generic-kernel targets; fragile
   CMake detection of OpenCL/ICD-loader; a standing request that `kcache`
   not require LLVM on a cache hit.
4. **LLVM 24** is still pre-release (in-progress as of mid-2026). No version-
   bump pressure yet, but worth a periodic check — a real share of this
   project's findings (the `VecFuncs.def` gaps, the LLVM 23 frexp/SLP bug)
   live in LLVM's own vectorizer, not PoCL.
5. **CERN's Debian 13 migration** (~2,200 accelerator-control computers,
   reported Sept 2026): RHEL raised its default compiler baseline
   (`x86-64-v2`/`v3` depending on the source) and left roughly two-thirds of
   that fleet behind, so CERN moved OS instead of hardware. No direct
   integration point exists — that fleet isn't an OpenCL workload, and CERN
   openlab has no PoCL relationship — but it's real, current, motivating
   context for #2310's argument (safe codegen across a wide spread of aging
   x86-64 CPUs matters beyond one AMD APU).

## Dependencies

Core (required to build at all):
- **LLVM + Clang** (dev headers/libs, version-matched) — the compiler
  backend PoCL's kernel compiler is built on. Tested here against 22 and 23.
- **CMake** ≥ 3.15, **make** or **ninja**, **pkg-config**
- **pthread** (system)
- **Python 3** ≥ 3.8 — SPIR bitcode support (on by default)

Needed for the work this repo actually does:
- **SLEEF** — vectorized math library; `ENABLE_CONFORMANCE` requires it.
  System-installed, found via `find_library`, not vendored. See the version
  note above.
- **glibc libmvec** — the other vector-math source the deny-list series
  chooses between per function.
- **OpenCL-CTS** (Khronos conformance test suite) — separate clone, drives
  the acceptance sweep this project's numbers are graded against.

Optional, PoCL-wide (not exercised by this project's work but present in the
build):
- **hwloc** ≥ 1.0 — topology detection
- **llvm-spirv** + **spirv-tools** — SPIR-V support (CPU/CUDA)
- **clspv** — the Vulkan driver's SPIR-V path; also the tool at the center
  of the original April attempt (see `../pocl/README.md`)
- **ocl-icd** (ICD loader, ≥ 2.3.0 for OpenCL 3.0) + **OpenCL-Headers**
- **CUDA Toolkit** / **Vulkan SDK** — only if building those drivers
- TBB, OpenMP, ONNX Runtime, OpenCV, libjpeg-turbo — assorted optional
  extensions, not used here

Python side (this repo's harness):
- **PyOpenCL**, **NumPy**, **mpmath** — all present in the
  `pocl-cpu-dev:llvm22` Docker image already on this machine.

## Repo layout

This repo is the **sidecar** — docs, harness, project history. It holds no
PoCL source itself:

- `harness/` — the ULP-sweep test harness (rebuilt 2026-09-15; see
  `RECOVERY.md` for exactly what was reconstructed vs. what's still missing)
- `results/` — sweep output JSON
- `RECOVERY.md` — the detailed account of what was lost 2026-09-12 and what
  came back 2026-09-15
- `../pocl-src/` — the actual upstream PoCL checkout + git worktrees per
  branch (recreated as a git worktree of this repo's fetched PR branches;
  originally a set of separate worktree checkouts per the notes)
- `../pocl-work/` — build output directories (e.g. `build-conf-vec-fix/`)

## How to resume

Build (12 threads; adjust `--cpuset-cpus` to the budget granted for the
session — standing default is cores 0-5, wider grants are per-instance):

```bash
docker run --rm --cpuset-cpus=0-11 \
  -v ~/dev/pocl-src:/work/src \
  -v ~/dev/pocl-work/build-conf-vec-fix:/work/build \
  -w /work/build \
  pocl-cpu-dev:llvm22 \
  bash -c "cmake /work/src -DCMAKE_BUILD_TYPE=Release && make -j12"
```

Run the harness (wimpy = quick spot check at widths 1,4; full = all widths):

```bash
docker run --rm --cpuset-cpus=0-11 \
  -v ~/dev/openpocl:/work/harness_src \
  -v ~/dev/pocl-src:/work/src \
  -v ~/dev/pocl-work/build-conf-vec-fix:/work/build \
  -e OCL_ICD_VENDORS=/work/build/ocl-vendors \
  -e POCL_BUILDING=1 -e POCL_CACHE_DIR=/tmp/poclcache -e PYOPENCL_NO_CACHE=1 \
  -w /work/harness_src \
  pocl-cpu-dev:llvm22 \
  python3 -m harness.sweep --mode full --out results/sweep-$(date +%Y%m%d).json
```

Note: any file a container writes into a bind-mounted `~/dev` path comes out
**root-owned** (containers run as root by default) — `docker run --rm -v
<path>:/target alpine chown -R 1000:1000 /target` fixes it without needing a
sudo password.

Next real decision is upstream: re-file the 4 recovered PRs from `anun333`
(content unchanged, closed only because the old account vanished) — held for
now per Seth's instruction.
