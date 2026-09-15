#!/usr/bin/env python3
"""
ULP sweep against a built PoCL. Reconstructed 2026-09-15 -- see common.py
docstring for what's known-original vs. reconstructed-from-notes.

Usage (inside the pocl-cpu-dev container, PoCL built + OCL_ICD_VENDORS
pointed at the build's ocl-vendors/ dir):

    python3 -m harness.sweep --mode wimpy
    python3 -m harness.sweep --mode full --funcs exp,log1p,pow --widths 1,4,8
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import mpmath

from . import common as C
from . import funcs as F

WIMPY_WIDTHS = [1, 4]
FULL_WIDTHS = [1, 2, 3, 4, 8]


def run_unary(ctx, dev, name, cl_name, domain_fn, mp_fn, bound, precision, width, n, rng, ftz_relax):
    dtype = C.DTYPE[precision]
    cl_type = C.CL_TYPE[precision]
    samples = domain_fn(n, dtype, rng)
    samples = C.shuffled_lanes(samples, width, rng)
    n_vectors = len(samples) // width

    src = C.vload_kernel(cl_name, width, cl_type, arity=1)
    out = C.run_kernel(ctx, dev, src, [samples], n_vectors, width, cl_type, dtype)

    max_ulp = 0.0
    worst_x = None
    for x, r in zip(samples, out):
        ref = mp_fn(mpmath.mpf(float(x)))
        e = C.ulp_error(r, ref, dtype)
        if ftz_relax and abs(float(x)) < float(np.finfo(dtype).tiny) * 4:
            continue  # near-denormal input on a flush-to-zero device
        if e > max_ulp:
            max_ulp, worst_x = e, float(x)
    return {"function": name, "precision": precision, "width": width,
            "max_ulp": max_ulp, "bound": bound, "pass": max_ulp <= bound,
            "n": n_vectors, "worst_x": worst_x}


def run_binary(ctx, dev, name, cl_name, domain0, domain1, mp_fn, bound, precision, width, n, rng):
    dtype = C.DTYPE[precision]
    cl_type = C.CL_TYPE[precision]
    a = domain0(n, dtype, rng)
    b = domain1(n, dtype, rng)
    m = (min(len(a), len(b)) // width) * width
    a, b = a[:m], b[:m]
    n_vectors = m // width

    src = C.vload_kernel(cl_name, width, cl_type, arity=2)
    out = C.run_kernel(ctx, dev, src, [a, b], n_vectors, width, cl_type, dtype)

    max_ulp = 0.0
    worst = None
    for x, y, r in zip(a, b, out):
        ref = mp_fn(mpmath.mpf(float(x)), mpmath.mpf(float(y)))
        e = C.ulp_error(r, ref, dtype)
        if e > max_ulp:
            max_ulp, worst = e, (float(x), float(y))
    return {"function": name, "precision": precision, "width": width,
            "max_ulp": max_ulp, "bound": bound, "pass": max_ulp <= bound,
            "n": n_vectors, "worst_xy": worst}


def run_int_arg(ctx, dev, name, cl_name, domain0, mp_fn, bound, precision, width, n, rng):
    dtype = C.DTYPE[precision]
    cl_type = C.CL_TYPE[precision]
    a = domain0(n, dtype, rng)
    ints = C.sample_small_int(n, rng)
    m = (min(len(a), len(ints)) // width) * width
    a, ints = a[:m], ints[:m]
    n_vectors = m // width

    src = C.vload_kernel(cl_name, width, cl_type, arity=1, int_arg_index=1)
    out = C.run_kernel(ctx, dev, src, [a], n_vectors, width, cl_type, dtype, int_buf=ints)

    max_ulp = 0.0
    worst = None
    for x, k, r in zip(a, ints, out):
        ref = mp_fn(mpmath.mpf(float(x)), int(k))
        e = C.ulp_error(r, ref, dtype)
        if e > max_ulp:
            max_ulp, worst = e, (float(x), int(k))
    return {"function": name, "precision": precision, "width": width,
            "max_ulp": max_ulp, "bound": bound, "pass": max_ulp <= bound,
            "n": n_vectors, "worst_x_n": worst}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["wimpy", "full"], default="wimpy")
    ap.add_argument("--funcs", default="all")
    ap.add_argument("--widths", default=None, help="override widths, e.g. 1,4,8")
    ap.add_argument("--precision", default="float,double")
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ftz", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    widths = [int(w) for w in args.widths.split(",")] if args.widths else (
        WIMPY_WIDTHS if args.mode == "wimpy" else FULL_WIDTHS)
    wanted = F.ALL_NAMES if args.funcs == "all" else args.funcs.split(",")
    precisions = args.precision.split(",")

    ctx, dev = C.get_pocl_context()
    print(f"device: {dev.name} ({dev.platform.name})", file=sys.stderr)

    rows = []
    t0 = time.time()
    for precision in precisions:
        ftz_relax = False
        if args.ftz == "auto":
            ftz_relax = not C.device_supports_denormals(dev, precision)
        elif args.ftz == "on":
            ftz_relax = True

        for width in widths:
            for name, cl_name, domain, mp_fn, bound in F.UNARY:
                if name not in wanted:
                    continue
                rows.append(run_unary(ctx, dev, name, cl_name, domain, mp_fn, bound,
                                       precision, width, args.samples, rng, ftz_relax))
            for name, cl_name, d0, d1, mp_fn, bound in F.BINARY + F.POWR:
                if name not in wanted:
                    continue
                rows.append(run_binary(ctx, dev, name, cl_name, d0, d1, mp_fn, bound,
                                        precision, width, args.samples, rng))
            for name, cl_name, d0, mp_fn, bound in F.INT_ARG:
                if name not in wanted:
                    continue
                rows.append(run_int_arg(ctx, dev, name, cl_name, d0, mp_fn, bound,
                                         precision, width, args.samples, rng))

    elapsed = time.time() - t0
    passed = sum(1 for r in rows if r["pass"])
    total = len(rows)

    print(f"\n{'function':10s} {'prec':7s} {'w':>2s} {'max_ulp':>10s} {'bound':>6s}  status")
    for r in sorted(rows, key=lambda r: (-((r["max_ulp"] / r["bound"]) if r["bound"] else 0))):
        status = "OK" if r["pass"] else "FAIL"
        print(f"{r['function']:10s} {r['precision']:7s} {r['width']:2d} "
              f"{r['max_ulp']:10.4f} {r['bound']:6.1f}  {status}")

    print(f"\nsweep {passed}/{total}  ({elapsed:.1f}s, mode={args.mode}, seed={args.seed})")

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps({
            "mode": args.mode, "seed": args.seed, "elapsed_s": elapsed,
            "passed": passed, "total": total, "rows": rows,
        }, indent=2))
        print(f"wrote {outp}", file=sys.stderr)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
