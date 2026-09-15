#!/usr/bin/env python3
"""Exact replica of the original discovery script (found in the session
transcript, openpocl a7e4392a..., line 1513) that first found the trig
lane cross-talk bug -- computing cos+sin+tan together, 7 distinct test
vectors as separate work items, local_work_size left to the driver."""
import numpy as np
import pyopencl as cl

dev = [p for p in cl.get_platforms() if "Portable" in p.name][0].get_devices()[0]
print(f"device: {dev.name}")
ctx = cl.Context([dev])
q = cl.CommandQueue(ctx)
src = """__kernel void k(__global const float4* a, __global float4* c, __global float4* s, __global float4* t){
  size_t i=get_global_id(0); c[i]=cos(a[i]); s[i]=sin(a[i]); t[i]=tan(a[i]); }"""
prg = cl.Program(ctx, src).build(cache_dir=False)
fmin = np.float32(1.1754943508222875e-38)
fmax = np.float32(3.4028234663852886e+38)
cases = {
    "neighbour 1.0": [fmin, 1, 1, 1],
    "neighbour FLT_MAX": [fmin, fmax, 1, 1],
    "neighbour inf": [fmin, np.inf, 1, 1],
    "neighbour nan": [fmin, np.nan, 1, 1],
    "neighbour 1e28": [fmin, 1e28, 1, 1],
    "neighbour 1e10": [fmin, 1e10, 1, 1],
    "neighbour 1e8": [fmin, 1e8, 1, 1],
    "neighbour 200": [fmin, 200, 1, 1],
}
a = np.array([cases[k] for k in cases], dtype=np.float32).reshape(-1, 4)
mf = cl.mem_flags
ab = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
outs = [cl.Buffer(ctx, mf.WRITE_ONLY, a.nbytes) for _ in range(3)]
prg.k(q, (len(a),), None, ab, *outs)
res = [np.empty_like(a) for _ in range(3)]
for r, b in zip(res, outs):
    cl.enqueue_copy(q, r, b)
q.finish()
for i, k in enumerate(cases):
    print(f"{k:18s} cos(FLT_MIN)={res[0][i,0]!r:22} sin={res[1][i,0]!r:24} tan={res[2][i,0]!r}")
