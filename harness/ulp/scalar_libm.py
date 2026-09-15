#!/usr/bin/env python3
"""
Measure ULP of the host's scalar glibc libm, independent of PoCL -- the
ground-truth baseline the sweep's PoCL numbers get compared against.
Named/described directly in the recovered notes:
"harness/ulp/scalar_libm.py and libmvec_direct.py measure both without PoCL."

Calls libm via ctypes rather than Python's math module so the exact glibc
symbol resolution matches what a C program (and PoCL's generated code) links.
"""
import argparse
import ctypes
import ctypes.util
import sys

import numpy as np
import mpmath

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import common as C  # noqa: E402

BASE_NAMES = ["sin", "cos", "tan", "exp", "log", "log1p", "log2", "log10",
              "expm1", "cbrt", "erf", "erfc", "tgamma", "asinh", "acosh", "atanh"]
# (c symbol name, base name) pairs -- keeps the float-suffix stripping from
# colliding with base names that themselves end in "f" (erf, erfc).
FUNCS_F64 = [(b, b) for b in BASE_NAMES]
FUNCS_F32 = [(b + "f", b) for b in BASE_NAMES]

MP = {
    "sin": mpmath.sin, "cos": mpmath.cos, "tan": mpmath.tan,
    "exp": mpmath.exp, "log": mpmath.log, "log1p": mpmath.log1p,
    "log2": lambda x: mpmath.log(x, 2), "log10": mpmath.log10,
    "expm1": mpmath.expm1, "cbrt": mpmath.cbrt, "erf": mpmath.erf,
    "erfc": mpmath.erfc, "tgamma": mpmath.gamma, "asinh": mpmath.asinh,
    "acosh": mpmath.acosh, "atanh": mpmath.atanh,
}


def domain_for(base):
    if base in ("log", "log2", "log10", "cbrt"):
        return "positive"
    if base == "tgamma":
        return "gamma"
    if base == "log1p":
        return "gt_neg1"
    if base == "acosh":
        return "ge1"
    if base == "atanh":
        return "pm1"
    if base in ("erf", "erfc"):
        return "moderate"
    return "any"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--precision", choices=["float", "double"], default="double")
    ap.add_argument("--samples", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    libm_path = ctypes.util.find_library("m")
    libm = ctypes.CDLL(libm_path)
    rng = np.random.default_rng(args.seed)
    dtype = C.DTYPE[args.precision]
    funcs = FUNCS_F32 if args.precision == "float" else FUNCS_F64
    c_t = ctypes.c_float if args.precision == "float" else ctypes.c_double

    print(f"libm: {libm_path}")
    print(f"{'function':10s} {'max_ulp':>10s} {'n':>6s}")
    for cname, base in funcs:
        fn = getattr(libm, cname)
        fn.restype = c_t
        fn.argtypes = [c_t]

        domain = domain_for(base)
        sampler = {
            "positive": C.sample_positive, "gt_neg1": C.sample_gt_neg1,
            "ge1": C.sample_ge1, "pm1": C.sample_pm1, "any": C.sample_any,
            "moderate": C.sample_moderate, "gamma": C.sample_gamma_domain,
        }[domain]
        xs = sampler(args.samples, dtype, rng)

        max_ulp = 0.0
        for x in xs:
            r = fn(c_t(float(x)))
            ref = MP[base](mpmath.mpf(float(x)))
            e = C.ulp_error(r, ref, dtype)
            max_ulp = max(max_ulp, e)
        print(f"{base:10s} {max_ulp:10.4f} {len(xs):6d}")


if __name__ == "__main__":
    main()
