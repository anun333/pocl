# PoCL Revitalization

Prove that [PoCL](https://github.com/pocl/pocl) (Portable Computing Language,
an open OpenCL implementation) is a real, fully-open compute path for
hardware the proprietary vendor stacks have abandoned — starting with cheap,
old AMD GPUs (MI25/MI50: ROCm no longer supports them) and, by extension,
any aging x86-64 fleet. The constraint that shaped every pivot below: **$0
hardware, all software** — the fix has to be upstream and open, not a
workaround that only helps one machine.

## The founding brief — this was the plan from message one

Before `git init`, before any PoCL investigation, the very first message of
the September session was a handoff brief titled "Project intent: PoCL
revitalization." Worth quoting because it means everything below wasn't
discovered mid-session — it was the plan going in.

The brief already knew PoCL's problem going in: *"Vectorized math builtin
libraries (SLEEF/libmvec/SVML) exist but only build with conformance
disabled."* Its 5-item priority roadmap:

1. **AMD backend via LLVM's AMDGPU directly**, bypassing ROCm's
   supported-hardware list — *"so EOL'd GCN/Polaris/Vega hardware stays
   alive."* The same rescue-abandoned-hardware goal as the original April
   `pocl`/clspv attempt ([`../pocl/README.md`](../pocl/README.md)), now
   properly scoped as one front among five instead of the whole project.
2. **"CPU performance — reconcile the conformance-vs-vectorized-math-library
   tradeoff."** This exact goal, named explicitly, second in priority from
   the start. This is the front that became this repo's actual work.
3. CUDA backend parity
4. Remote driver as a real distributed scheduler
5. Custom accelerator targeting (FPGA/ASIC)

**The "why," verbatim from the brief:** *"the goal is that vendor EOL stops
bricking functional silicon, that one kernel runs across CPU/old GPU/
RISC-V/remote device, and that there's a compute stack with no proprietary
link anywhere in it."* Seth's own words shortly after, independent of the
brief: *"where could a pocl overhaul benefit old hardware and those with
less money who don't want to be locked up into cuda and other close[d]
libraries."*

**Why CPU vecmath specifically, out of five fronts** — a deliberate
triage, stated in the same brief: *"the verifiable work (vectorizer, math
builtins, numerics) is doable without exotic hardware and is checkable
against the OpenCL CTS and a bit-exact CPU reference — that's where I'd
start, and it suits long autonomous agent runs. Backend bring-up needs
hardware in the loop and a long-term maintainer commitment; scope that
honestly."*

So, honestly: **priority #1 (AMD/EOL-hardware rescue) is the actual point
of the whole project, and it was never started.** Priority #2 (this repo)
was chosen instrumentally — objectively checkable, no special hardware
needed, suited to autonomous work — as the tractable on-ramp, not the
destination. Everything in this repo, including the 3-PR plan below, is
progress on the on-ramp, not the thing the on-ramp leads to.

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

## The actual destination: a 3-PR upstream plan, only 2 reached

The design doc that kicked off the September work (`docs/design/vecmath-allowlist.md`,
lost with the sidecar, recovered from the session transcript) laid out
*why* this had to start in the default/non-conformant build specifically,
and where it was headed. Worth stating plainly, because it's easy to
mistake this project for "fix some math bugs" when the actual goal was
bigger.

**The problem, in upstream's own architecture:** `ENABLE_HOST_CPU_VECTORIZE_{LIBMVEC,SLEEF,SVML}`
and `ENABLE_CONFORMANCE` were entangled as an all-or-nothing switch —
conformant (official, CTS-certified) builds banned vector math *entirely*,
because nobody had verified its ULP per function. That's why every bug
this project found lived only in the default "fast" build: conformant
builds never attempted the swap at all, so there was nothing there yet to
be buggy.

**The plan was three PRs, in order:**

1. **`pown`** — stop swapping it. Small, obviously correct, described in
   the design doc as existing specifically to *"establish contact"* with
   upstream before bigger asks. → filed as **#2307**.
2. **The filtered per-function allow/deny list itself** (the actual
   mechanism: measure every function, deny only what fails, generate the
   table from the harness) plus env overrides and FileCheck tests. Noted
   explicitly: *"No behaviour change for conformant builds"* at this
   stage — they still weren't using vector math. → filed as **#2311**
   (with #2308 and #2309 found and fixed along the way).
3. **"The switch split"** — split `ENABLE_CONFORMANCE` from vector-math
   enablement entirely, so PoCL's official CTS-certified builds could
   finally use fast vectorized math too, something upstream has never had.
   Evidence for this PR was meant to be **the full CTS run from Tampere's
   weekly job** — the same SLEEF-variant conformance run that paused at
   94/161 on 2026-09-06 and was deprioritized earlier this session. That
   characterization needs a correction: it isn't a minor secondary check,
   it's the specific evidence step 3 needed. **Step 3 itself was never
   started** — only steps 1 and 2 got filed before the pause.

So the honest state of this project isn't "4 bug fixes ready to re-file."
It's "2 of 3 planned PRs ready to re-file, with the actual destination —
fast *and* conformant vector math on PoCL CPU — not yet begun."

## Parked: RISC-V sensor-node proposal — never sent

On 2026-09-05, alongside the CTS/SLEEF work, a "Summary of Intent" document
was drafted for a RISC-V sensor-node use case built on PoCL — plus a
separate glass-house chip plan (a different project; not detailed here).
Saved as `docs/intent-riscv-sensor-nodes.md` in this repo (the downstream
picture, mapping to README priorities, five items with measurements,
decisions, needs) with a revised draft meant to post upstream as a **GitHub
Discussion with the PoCL maintainers.**

**It was never posted.** The notes are explicit: *"posting needs [Seth's]
go-ahead"* — that go-ahead was never given before the project paused the
next day. What looked like maintainer feedback in the session log was
Claude reviewing the draft internally, not real maintainers responding.
Nothing went out the door.

Decisions captured in the draft, from the session notes (the doc itself
is lost — never a PR, no upstream ref to recover it from):
- **PoCL-R (client-server, hub-and-spoke) vs. ROS2 (pub/sub)** as the
  compute-distribution model for sensor nodes
- Reframe one item toward the **AlmaIF accelerator path**
- RVA22/RVV1.0 wording corrections
- **Integer-only computation is the precondition** for cross-target
  bit-identical results across nodes

If this direction gets picked back up, it starts from a blank page on the
actual document — only these bullet points survived.

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
- Build verified clean: PoCL's own regression suite 146/146 (146 after
  rebase, was 144), harness sweep 250/250 (25 functions × widths 1/2/3/4/8
  × float/double) against the recovered `pr-2311-vecmath` branch.
- **Re-filed 2026-09-15, all 4**: [pocl/pocl#2319](https://github.com/pocl/pocl/pull/2319)
  (pown), [pocl/pocl#2320](https://github.com/pocl/pocl/pull/2320) (vecmath
  deny-list, includes #2309's trig fix as a prerequisite), and
  [pocl/pocl#2321](https://github.com/pocl/pocl/pull/2321) (api), all from
  `anun333`. Plus [llvm/llvm-project#223817](https://github.com/llvm/llvm-project/pull/223817)
  (VecFuncs.def, 48 entries).
- **#2320 is now a draft (2026-09-16).** Testing against narrower
  kernel-library variants found a regression *in this series*: the emitted
  vector-library call does not depend on the selected variant, so an
  SSE2-variant build emits the AVX2 `_ZGVdN4v_*` entry point and passes its
  argument in XMM while the callee reads YMM0 — wrong results above 128-bit
  widths. Confirmed at object-code level; disclosed upstream; see
  `RECOVERY.md` and `docs/draft-2320-comment.md`. **#2319 and #2321 are
  unaffected and remain ready for review** — and #2319 gained supporting
  evidence, since vanilla PoCL is genuinely broken for `pown` at sse2
  (760k-2.2e9 ULP) and the fix repairs it.

## Build-improvement opportunities (found 2026-09-15)

1. ~~SLEEF 3.5.1 → 3.9.0~~ **Correction (2026-09-15, after checking the build
   system directly):** the exp/log1p ULP failures #2311 denies were in
   **glibc's libmvec**, not SLEEF — the fix denies libmvec for those
   functions and falls back to SLEEF, which was the safe path the whole
   time ("both precisions back to the SLEEF source," per the original
   notes). SLEEF 3.8's log1p/exp/pow overflow-bound fix doesn't touch what
   this series actually denies; flagging it as relevant here earlier was a
   misattribution — same function names, different library, unrelated bug.
   Separately, and worth knowing regardless: PoCL doesn't link the system
   `libsleef` for its default kernel-library math at all — `lib/kernel/sleef/`
   is a **vendored copy baked directly into the pocl/pocl repo**, plain
   files with no CMakeLists or `.gitmodules`, not swappable via a
   `find_library`/prefix override. Bumping it is a maintainer-level
   vendor-import task, not something a downstream PR does in passing.
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
build) — **hwloc** ≥ 1.0 (topology), **llvm-spirv** + **spirv-tools**
(SPIR-V, CPU/CUDA), **ocl-icd** (ICD loader ≥ 2.3.0 for OpenCL 3.0) +
**OpenCL-Headers**. Everything else is gated behind a specific `ENABLE_*`
CMake flag, checked 2026-09-15:

| Flag | Dependency | Required? | Enables |
|---|---|---|---|
| `ENABLE_TBB_DEVICE` | TBB (oneTBB) | yes, if set | TBB-backed device driver |
| `ENABLE_HOST_CPU_DEVICES_OPENMP` | OpenMP | optional | OpenMP CPU driver variant |
| `ENABLE_RDMA` | RDMAcm + Verbs | yes, if set | RDMA transport for `pocld` remote/pooled compute — relevant if the RISC-V sensor-node pooled-compute angle is ever revived |
| `ENABLE_HOST_CPU_DEVICES AND NOT ENABLE_CONFORMANCE` | ONNX Runtime ≥1.17, libjpeg-turbo ≥3.0.0, OpenCV (dnn) | auto-detected, silently skipped if missing; **unavailable in conformance builds** | CPU-driver vision/DNN builtin kernels (ties to the OpenVX conformance work) |
| — nested in the block above — | BLAS | only if `LIBXSMM_FOUND` | libxsmm GEMM backend |
| `ENABLE_CUDA` | CUDA Toolkit (`cudart`) | yes, if set | CUDA driver |
| `ENABLE_VULKAN` | Vulkan SDK (required) + `clspv`/`clspv-reflection` (found, not strictly required) | Vulkan yes; clspv expected | Vulkan driver's SPIR-V path — **clspv is the same tool the original April project (`../pocl/README.md`) was built around** |
| `ENABLE_HSA` | `hsa_ext_amd.h` header | optional path lookup | HSA driver |
| `ENABLE_DOXYGEN` | Doxygen | yes, if set | API docs |

None of these flags are on in a plain CPU build, and none touch this
project's actual work (CPU vecmath, CTS).

Python side (this repo's harness):
- **PyOpenCL**, **NumPy**, **mpmath** — all present in the
  `pocl-cpu-dev:llvm22` Docker image already on this machine.

## Dependency & adjacent-project watch (checked 2026-09-15)

Direct hits — worth reading before touching the related work again:

- **LLVM `VecFuncs.def` gap is a real, open, tracked upstream issue:**
  [llvm/llvm-project#204678](https://github.com/llvm/llvm-project/issues/204678)
  ("Extend the x86_64 libmvec table in VecFuncs.def to the modern glibc set,"
  filed 2026-07-02, still open) is exactly the gap the already-drafted patch
  (`docs/upstream/llvm-vecfuncs-libmvec.md`, lost with the sidecar) targeted.
  Sibling issue [#206273](https://github.com/llvm/llvm-project/issues/206273)
  covers the same missing functions (erf, tan, tanh, exp2, log2...). A third,
  [#223283](https://github.com/llvm/llvm-project/issues/223283) (Darwin's
  libsystem_m has the same kind of gap), shows this is systemic, not a
  one-off — filing against #204678 lands on already-acknowledged interest.
- **SLEEF has a live SIGILL bug on old CPUs:**
  [shibatch/sleef#707](https://github.com/shibatch/sleef/issues/707) —
  "PURECFMA scalar dispatch causes SIGILL on x86-64-v2 CPUs (Sandy Bridge)."
  Same failure class as the CERN Debian-13 story above, in the same library
  this project links against.
- **SPIRV-LLVM-Translator has active frexp work right now:**
  [commit a4fcec59](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/commit/a4fcec59)
  (2026-09-14) "Emit llvm.frexp exponent OpVariable in the entry block" —
  frexp is exactly the area the unfiled `fix/no-frexp-swap` branch touched
  (the LLVM 23 vector-double pown/rootn/powr bug bisected to a frexp swap).
  Check whether this already covers it before redoing that fix.
- **OpenCL-CTS has PoCL-specific CI commits landing the same day as this
  check:** [commit 1a6f465f](https://github.com/KhronosGroup/OpenCL-CTS/commit/1a6f465f)
  "ci: PoCL build changes to pass more tests."

Everything else, by role:

| Project | Role | Notes |
|---|---|---|
| [llvm/llvm-project](https://github.com/llvm/llvm-project) | compiler backend | commits land hourly; see above |
| [shibatch/sleef](https://github.com/shibatch/sleef) | vector math lib | quiet since Dec 2025 (docs-only commits); #707 above; #227 open ("add more lower-accuracy options") |
| glibc (libmvec) | vector libm | tracked via sourceware Bugzilla, not GitHub — not checked here |
| [KhronosGroup/OpenCL-CTS](https://github.com/KhronosGroup/OpenCL-CTS) | conformance suite | very active daily; #2811 open (host float atomic add/sub vs SVM atomics incompatible) |
| [KhronosGroup/OpenCL-Headers](https://github.com/KhronosGroup/OpenCL-Headers) | API headers | active, nothing blocking |
| [KhronosGroup/OpenCL-ICD-Loader](https://github.com/KhronosGroup/OpenCL-ICD-Loader) | ICD loader | maintenance-level; #157 minor Linux leak in `khrIcdVendorAdd`, rest are Windows DllMain issues |
| [open-mpi/hwloc](https://github.com/open-mpi/hwloc) | topology (optional) | active, cosmetic only, nothing relevant |
| [KhronosGroup/SPIRV-LLVM-Translator](https://github.com/KhronosGroup/SPIRV-LLVM-Translator) | SPIR-V (optional) | very active; see above |
| [KhronosGroup/SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools) | SPIR-V (optional) | very active; only spirv-fuzz issues open, not relevant to normal builds |
| [google/clspv](https://github.com/google/clspv) | Vulkan SPIR-V path; **also the core tool of the original April project** ([`../pocl/`](../pocl/README.md)) | active; #1608 opaque-pointer crash, #1350/#1355 addrspace-cast lowering bugs on `llvm.memcpy` — relevant if that thread is ever revisited |
| Mesa/Rusticl | GPU path (RadeonSI) | on GitLab, not GitHub; Mesa 26.1/26.2 had active RadeonSI/Rusticl APU fixes. Own notes already found general rusticl crashes fixed on Mesa 26.2.2; the specific exp10/half_exp10/fma segfault (found on Mesa 25.2.8) was never retested there or filed |

## Suggested work, in order (2026-09-15)

**Tier 1 — ready now, no new investigation needed**

1. ~~Re-file all 4 recovered PRs from `anun333`~~ — **done**, see Current state.
2. File the `VecFuncs.def` patch against the real open upstream issue (`llvm/llvm-project#204678`) — needs rebuilding from the 12-function gap list first (lost with the sidecar), but has a live target to file against.

**Tier 2 — continuing the actual front-#2 work (CPU vecmath)**

3. Stand up PR 3 — **"the switch split"**: enable libmvec/SLEEF under `ENABLE_CONFORMANCE`. The real destination of front #2, never started.
4. Rebuild and run the SLEEF-variant full CTS conformance suite (paused at 94/161, 2026-09-06) — the specific evidence PR 3 needs, not a secondary check. Re-clone OpenCL-CTS, rewrite the resume driver (lost).
5. Investigate the SSE2 wide-vector-width bug found tonight (float8/double4/double8 → garbage under forced SSE2, narrower widths clean) — not yet filed anywhere, directly CERN-relevant.
6. Redo `feat/veclib-direct` (3.4x-faster direct-libmvec approach, A/B-tested, prose-only now) and `fix/no-frexp-swap` (confirmed still needed — the SPIRV-LLVM-Translator frexp fix found tonight was unrelated) from the session notes.
7. Fill the two harness gaps: multi-output builtins (fract/modf/frexp/remquo/sincos), determinism harness (`int_kernels.py`).

**Tier 3 — decisions needed, not yet actioned**

8. RISC-V sensor-node proposal: revive (PoCL-R vs ROS2, now informed by the front-#4 remote-driver context below) or formally shelve.
9. Known-bug follow-ups: check whether this project's code path touches SLEEF's PURECFMA scalar dispatch (`sleef#707`, SIGILL on x86-64-v2); retest the Rusticl exp10/fma segfault on Mesa 26.2.2.

**Tier 4 — the other 4 fronts of the founding roadmap (not started, bigger scope)**

10. AMD backend via LLVM's AMDGPU directly — front #1, the actual point of the whole project, needs real AMD hardware in the loop.
11. CUDA backend parity (front #3).
12. Remote driver as a real distributed scheduler (front #4) — where the RISC-V sensor-node idea would actually live.
13. Custom accelerator targeting / FPGA-ASIC OpenCL front end (front #5).

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
