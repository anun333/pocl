#!/usr/bin/env python3
"""Reconfirm the exact claims made in the recovered commit messages, against
a real build, rather than trusting the commit prose. Each check uses the
precise cited input, not random sampling (the whole point of these bugs is
that random sampling misses them)."""
import struct
import sys

import pyopencl as cl
import mpmath

mpmath.mp.dps = 50


def run_kernel(ctx, dev, src, kernel_name, inputs, out_dtype, out_len,
                global_size=None, local_size=None, build_opts=""):
    import numpy as np
    prg = cl.Program(ctx, src).build(options=build_opts)
    queue = cl.CommandQueue(ctx, dev)
    mf = cl.mem_flags
    bufs = [cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=i) for i in inputs]
    out_host = np.empty(out_len, dtype=out_dtype)
    out_cl = cl.Buffer(ctx, mf.WRITE_ONLY, out_host.nbytes)
    gs = global_size if global_size is not None else (out_len,)
    getattr(prg, kernel_name)(queue, gs, local_size, *bufs, out_cl)
    cl.enqueue_copy(queue, out_host, out_cl)
    queue.finish()
    return out_host


def get_ctx():
    for plat in cl.get_platforms():
        if "portable computing language" in plat.name.lower():
            devs = plat.get_devices()
            return cl.Context(devices=devs), devs[0]
    raise RuntimeError("no PoCL platform found")


def ulp(computed, ref_mp, npdtype):
    import numpy as np
    ref = npdtype(float(ref_mp))
    nxt = np.nextafter(ref, npdtype(np.inf) if ref >= 0 else npdtype(-np.inf))
    spacing = abs(float(nxt) - float(ref))
    if spacing == 0:
        spacing = float(np.finfo(npdtype).tiny)
    diff = abs(mpmath.mpf(float(computed)) - ref_mp)
    return float(diff / mpmath.mpf(spacing))


def main():
    import numpy as np
    ctx, dev = get_ctx()
    print(f"device: {dev.name}\n")

    # --- exp: the exact bit pattern from commit 5595cfaa7 ---
    # The bug is specifically in the libmvec-ABI vector call the LOOP
    # VECTORIZER swaps in when a scalar-typed kernel runs over many work
    # items (_ZGVbN2v_exp / _ZGVdN4v_exp) -- not explicit vector types, and
    # NOT a single work item (nothing for the loop vectorizer to pack). A
    # literal constant would also risk being constant-folded at compile
    # time through a different (host libm) path entirely, so the value
    # must come from a buffer, over enough work items to force
    # vectorization.
    x_expected = -float.fromhex('0x1.31000000000d0p-6')
    print(f"exp claim: x=-0x1.31000000000d0p-6 = {x_expected!r}")
    N = 64
    src = """
    __kernel void k(__global const double* in, __global double* out) {
        int i = get_global_id(0);
        out[i] = exp(in[i]);
    }"""
    inp = np.full(N, x_expected, dtype=np.float64)
    out = run_kernel(ctx, dev, src, "k", [inp], np.float64, N, local_size=(4,))
    ref = mpmath.exp(mpmath.mpf(x_expected))
    out_all = out
    out = out[:1]  # all N lanes are identical input; inspect one
    print(f"  all {N} lanes identical result: {bool(np.all(out_all == out_all[0]))}")
    got_hex = out[0].hex()
    expected_hex = float.fromhex('0x1.f68e9226f16cep-1')
    print(f"  got:      {out[0]!r}  ({got_hex})")
    print(f"  cited result: {expected_hex!r}  (0x1.f68e9226f16cep-1)")
    print(f"  match cited result: {out[0] == expected_hex}")
    print(f"  ULP vs correctly-rounded reference: {ulp(out[0], ref, np.float64):.4f}  (claimed 3.0077)")
    print()

    # --- log1p: two exact bit patterns from commit 74ccc7fc6 ---
    # Same reasoning as exp: needs the loop-vectorizer/libmvec-swap path,
    # buffer-sourced so it can't be constant-folded.
    print("log1p claims:")
    xf = float.fromhex('0x1.55a146p-2')
    src_f = """
    __kernel void k(__global const float* in, __global float* out) {
        int i = get_global_id(0);
        out[i] = log1p(in[i]);
    }"""
    inp = np.full(N, xf, dtype=np.float32)
    out = run_kernel(ctx, dev, src_f, "k", [inp], np.float32, N, local_size=(8,))[:1]
    ref = mpmath.log1p(mpmath.mpf(xf))
    print(f"  float  x=0x1.55a146p-2: got {out[0]!r}, ULP={ulp(out[0], ref, np.float32):.4f}  (claimed 2.004)")

    xd = float.fromhex('0x1.0000000000201p-11')
    src_d = """
    __kernel void k(__global const double* in, __global double* out) {
        int i = get_global_id(0);
        out[i] = log1p(in[i]);
    }"""
    inp = np.full(N, xd, dtype=np.float64)
    out = run_kernel(ctx, dev, src_d, "k", [inp], np.float64, N, local_size=(4,))[:1]
    ref = mpmath.log1p(mpmath.mpf(xd))
    print(f"  double x=0x1.0000000000201p-11: got {out[0]!r}, ULP={ulp(out[0], ref, np.float64):.4f}  (claimed 2.524)")
    print()

    # --- trig lane cross-talk: the exact repro from commit 3a7a4b970 ---
    # Load from a buffer, not literal constants -- literals risk being
    # constant-folded by the compiler through a completely different path,
    # never touching __pocl_argReductionS at all.
    print("trig lane cross-talk claim: sin((float4)(FLT_MIN, 1e8f, 1, 1)).x")
    FLT_MIN = np.finfo(np.float32).tiny
    src_v = """
    __kernel void k(__global const float4* in, __global float* out) {
        float4 v = in[0];
        float4 r = sin(v);
        out[0] = r.x;
        out[1] = r.y;
        out[2] = r.z;
        out[3] = r.w;
    }"""
    N2 = 32
    src_v2 = """
    __kernel void k2(__global const float4* in, __global float* out) {
        int i = get_global_id(0);
        float4 r = sin(in[i]);
        out[i] = r.x;
    }"""
    vec_in_multi = np.tile(np.array([FLT_MIN, 1e8, 1.0, 1.0], dtype=np.float32), (N2, 1))
    out_multi = run_kernel(ctx, dev, src_v2, "k2", [vec_in_multi], np.float32, N2, local_size=(4,))
    print(f'  multi-WI (N={N2}, local=4) lane-0 results: got {out_multi[0]!r}, all identical: {bool((out_multi == out_multi[0]).all())}')

    vec_in = np.array([FLT_MIN, 1e8, 1.0, 1.0], dtype=np.float32)
    out = run_kernel(ctx, dev, src_v, "k", [vec_in], np.float32, 4, global_size=(1,))
    correct_x = float(mpmath.sin(mpmath.mpf(float(FLT_MIN))))
    print(f"  lane 0 (FLT_MIN={FLT_MIN!r}): got {out[0]!r}, correct ~= {correct_x!r}")
    print(f"  claimed broken result: 0.0078124 -- got matches claim: {abs(out[0] - 0.0078124) < 1e-6}")
    print(f"  claimed FIXED result should equal FLT_MIN: {abs(out[0] - FLT_MIN) < 1e-30}")


if __name__ == "__main__":
    main()
