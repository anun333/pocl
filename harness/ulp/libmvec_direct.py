#!/usr/bin/env python3
"""
Measure ULP of glibc's vectorized libmvec symbols directly (no PoCL).
Companion to scalar_libm.py -- named together in the recovered notes:
"harness/ulp/scalar_libm.py and libmvec_direct.py measure both without PoCL."

_ZGV<isa>N<width>v_<name> entry points use the x86-64 vector-register calling
convention (arguments/results live in a YMM/ZMM register, not memory), which
ctypes cannot call directly. This compiles a tiny pointer-based C shim on the
fly (matches the notes' "glibc probe via the target compiler, not ldd") and
calls the real libmvec symbol through it, so the ABI is handled by the
compiler instead of hand-rolled in Python.

ABI letters (x86-64): b = SSE2 (128-bit, -msse2), d = AVX2 (256-bit, -mavx2).
"""
import argparse
import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import mpmath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import common as C  # noqa: E402

FUNCS = [
    ("exp", mpmath.exp, "any"),
    ("log", mpmath.log, "positive"),
    ("sin", mpmath.sin, "periodic"),
    ("cos", mpmath.cos, "periodic"),
    ("log1p", mpmath.log1p, "gt_neg1"),
    ("exp10", lambda x: mpmath.power(10, x), "any"),
]

ABI = {
    "b": {"width": 2, "cflag": "-msse2", "vecsize": 16},
    "d": {"width": 4, "cflag": "-mavx2", "vecsize": 32},
}

SHIM_TEMPLATE = """
#include <math.h>
typedef double vecd __attribute__((vector_size({vecsize})));
extern vecd _ZGV{abi}N{width}v_{name}(vecd);
void shim_{name}(double* in, double* out) {{
    vecd v;
    for (int i = 0; i < {width}; i++) v[i] = in[i];
    vecd r = _ZGV{abi}N{width}v_{name}(v);
    for (int i = 0; i < {width}; i++) out[i] = r[i];
}}
"""


def build_shim(names, abi, tmpdir):
    cfg = ABI[abi]
    src = "\n".join(SHIM_TEMPLATE.format(abi=abi, width=cfg["width"],
                                          vecsize=cfg["vecsize"], name=n)
                     for n in names)
    src_path = Path(tmpdir) / "shim.c"
    so_path = Path(tmpdir) / "shim.so"
    src_path.write_text(src)
    subprocess.run(
        ["gcc", "-shared", "-fPIC", cfg["cflag"], "-O2",
         str(src_path), "-o", str(so_path), "-lmvec", "-lm"],
        check=True, capture_output=True, text=True)
    return ctypes.CDLL(str(so_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--abi", choices=["b", "d"], default="d")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    dtype = C.DTYPE["double"]
    width = ABI[args.abi]["width"]
    names = [n for n, _, _ in FUNCS]

    with tempfile.TemporaryDirectory() as tmp:
        try:
            shim = build_shim(names, args.abi, tmp)
        except subprocess.CalledProcessError as e:
            print("shim build failed:\n" + e.stderr, file=sys.stderr)
            sys.exit(1)

        print(f"abi={args.abi} width={width} (compiled shim over libmvec)")
        print(f"{'function':10s} {'symbol':22s} {'max_ulp':>10s} {'status':>8s}")
        for name, mp_fn, domain in FUNCS:
            fn = getattr(shim, f"shim_{name}")
            fn.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
            fn.restype = None

            sampler = {"any": C.sample_any, "positive": C.sample_positive,
                       "periodic": C.sample_periodic, "gt_neg1": C.sample_gt_neg1}[domain]
            xs = sampler((args.samples // width) * width, dtype, rng)

            max_ulp = 0.0
            in_buf = (ctypes.c_double * width)()
            out_buf = (ctypes.c_double * width)()
            for i in range(0, len(xs), width):
                chunk = xs[i:i + width]
                for k, v in enumerate(chunk):
                    in_buf[k] = float(v)
                fn(in_buf, out_buf)
                for x, r in zip(chunk, out_buf):
                    ref = mp_fn(mpmath.mpf(float(x)))
                    max_ulp = max(max_ulp, C.ulp_error(r, ref, dtype))
            sym = f"_ZGV{args.abi}N{width}v_{name}"
            print(f"{name:10s} {sym:22s} {max_ulp:10.4f}       OK")


if __name__ == "__main__":
    main()
