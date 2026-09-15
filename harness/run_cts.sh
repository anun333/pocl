#!/bin/bash
# Full OpenCL CTS run against a PoCL build, parallel + resumable.
#
# Rebuilt 2026-09-16. The original chain (resume-sleef-full.sh, full_parallel.sh
# and friends) was lost with the sidecar repo; this is a replacement built to the
# shape the session notes describe:
#
#   - math_brute_force is the long pole (~87h serial in the original run), so its
#     105 sub-tests are run N at a time rather than as one process
#   - one log line per completed sub-test, so progress survives a crash
#   - already-logged sub-tests are skipped on restart -- that is the resume
#   - math runs with --num-worker-threads 1; the notes call this out explicitly,
#     results are not reproducible otherwise
#   - thread budget: 12 processes x 1 PoCL compute unit (POCL_CPU_MAX_CU_COUNT=1)
#     x 1 threadpool thread, so total threads ~= cores. Left at defaults this
#     was 336 threads on 12 cores (load ~100). Limiting CUs is safe for the
#     math tests -- they measure per-element accuracy, which does not depend on
#     how work is spread across compute units. The non-math suites run serially
#     and get the whole device, so nothing is under-exercised there.
#
# Run this INSIDE a detached container (docker run -d). Per the notes:
# "nohup chains started from the tool shell die with the editor; anything that
# must survive should run inside a container or under setsid/systemd-run."
#
# Usage:
#   JOBS=6 run_cts.sh <cts-build> <pocl-build> <logdir>
set -u

CTS="${1:?usage: run_cts.sh <cts-build> <pocl-build> <logdir>}"
POCL="${2:?}"
LOGDIR="${3:?}"
JOBS="${JOBS:-6}"

mkdir -p "$LOGDIR/out"
LOG="$LOGDIR/progress.log"
touch "$LOG"

export OCL_ICD_VENDORS="$POCL/ocl-vendors"
export POCL_BUILDING=1

done_already() { grep -qx "### done $1 .*" "$LOG" 2>/dev/null; }

# $1 = log key, rest = command
run_one() {
  local key="$1"; shift
  if done_already "$key"; then return 0; fi
  local start=$(date +%s)
  # Per-test kernel cache: caches collide between concurrent tests.
  POCL_CACHE_DIR="$LOGDIR/cache/$key" PYOPENCL_NO_CACHE=1 \
    POCL_CPU_MAX_CU_COUNT="${CU:-0}" \
    timeout 43200 "$@" > "$LOGDIR/out/$key.txt" 2>&1
  local rc=$?
  echo "### done $key rc=$rc secs=$(( $(date +%s) - start ))" >> "$LOG"
}

echo "=== run started $(date -Is) jobs=$JOBS pocl=$POCL ===" >> "$LOG"

# ---- math_brute_force, parallel by sub-test -------------------------------
MBF="$CTS/test_conformance/math_brute_force/test_bruteforce"
if [ -x "$MBF" ]; then
  mapfile -t FNS < <("$MBF" --list 2>/dev/null | tail -n +2 \
                     | tr -s ' \t' '\n' | grep -E '^[a-z_0-9]+$' | sort -u)
  echo "math sub-tests: ${#FNS[@]}" >> "$LOG"
  for fn in "${FNS[@]}"; do
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
    # -t 1: one threadpool thread per process. Without this each process
    # spawns ~28 threads, so 12-way parallelism became 336 threads on 12
    # cores (load ~100, thrashing). The notes also record "4-thread CTS
    # nondeterminism", so oversubscription risks flaky results on a run
    # whose whole point is trustworthy evidence.
    CU=1 run_one "math_$fn" "$MBF" --num-worker-threads 1 -t 1 "$fn" &
  done
  wait
fi

# ---- everything else, serially --------------------------------------------
# These are the ~24h-serial portion in the original run. Kept serial because
# several of them assume they own the device.
find "$CTS/test_conformance" -type f -executable -name 'test_*' \
  | grep -v math_brute_force | sort | while read -r exe; do
  key="$(basename "$(dirname "$exe")")"
  # Serial, so no contention: give each suite the whole device (CU unset =
  # PoCL default = all compute units), which is what a real user gets.
  ( cd "$(dirname "$exe")" && run_one "suite_$key" "$exe" )
done

echo "=== run finished $(date -Is) ===" >> "$LOG"
TOTAL=$(grep -c '^### done' "$LOG")
PASS=$(grep -c '^### done .* rc=0 ' "$LOG")
echo "=== TALLY: $PASS of $TOTAL exit 0 ===" >> "$LOG"
