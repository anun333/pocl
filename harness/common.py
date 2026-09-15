"""
Shared ULP-sweep machinery: reference values (mpmath), argument sampling,
device setup, OpenCL kernel generation/execution.

Reconstructed 2026-09-15 from prose in the recovered memory notes
(pocl-stage0-status.md / pocl-workspace-layout.md) after the original
harness/ source was lost with the sidecar repo. Behavior documented there
that this reimplements:
  - periodic functions (sin/cos/tan) get argument magnitudes sampled up to
    the largest finite float, not just [-pi, pi], to catch lane cross-talk
    in argument reduction
  - each vector lane gets an independently drawn magnitude ("shuffles
    magnitudes across lanes") rather than grouping similar magnitudes
  - --ftz auto: skip/relax denormal-range inputs when the device doesn't
    support denormals (CL_FP_DENORM bit)
  - ULP error is measured against an arbitrary-precision (mpmath) reference,
    as a fraction of the target dtype's local spacing -- this is why the
    original logs report fractional ULP values like "2.004" and "0.99/0.94",
    not integer ULP counts.
"""
import numpy as np
import mpmath
import pyopencl as cl

mpmath.mp.dps = 50  # decimal digits of precision for reference values

DTYPE = {"float": np.float32, "double": np.float64}
CL_TYPE = {"float": "float", "double": "double"}

# --------------------------------------------------------------------------
# Argument sampling
# --------------------------------------------------------------------------

def _finite_max(dtype):
    return float(np.finfo(dtype).max)


def sample_any(n, dtype, rng):
    """Full finite range, log-uniform magnitude, random sign."""
    fmax = _finite_max(dtype)
    fmin = float(np.finfo(dtype).tiny)
    mags = np.exp(rng.uniform(np.log(fmin), np.log(fmax), size=n))
    signs = rng.choice([-1.0, 1.0], size=n)
    return (mags * signs).astype(dtype)


def sample_periodic(n, dtype, rng):
    """Magnitudes up to the largest finite value -- stresses argument
    reduction far outside the primary period, per the documented sampler."""
    fmax = _finite_max(dtype)
    # mix: half "reasonable" range (0, 1e6), half up to fmax, to keep some
    # signal near the primary period as well as the pathological tail
    half = n // 2
    near = rng.uniform(0, 1e6, size=half)
    far = np.exp(rng.uniform(np.log(1e6), np.log(fmax), size=n - half))
    mags = np.concatenate([near, far])
    rng.shuffle(mags)
    signs = rng.choice([-1.0, 1.0], size=n)
    return (mags * signs).astype(dtype)


def sample_positive(n, dtype, rng):
    fmax = _finite_max(dtype)
    fmin = float(np.finfo(dtype).tiny)
    return np.exp(rng.uniform(np.log(fmin), np.log(fmax), size=n)).astype(dtype)


def sample_gt_neg1(n, dtype, rng):
    """For log1p: x > -1."""
    fmax = _finite_max(dtype)
    neg = rng.uniform(-1 + 1e-6, 0, size=n // 2)
    pos = np.exp(rng.uniform(-10, np.log(fmax), size=n - n // 2))
    out = np.concatenate([neg, pos])
    rng.shuffle(out)
    return out.astype(dtype)


def sample_ge1(n, dtype, rng):
    """For acosh: x >= 1."""
    return (1.0 + np.exp(rng.uniform(-10, 20, size=n))).astype(dtype)


def sample_pm1(n, dtype, rng):
    """For atanh: -1 < x < 1."""
    return rng.uniform(-1 + 1e-6, 1 - 1e-6, size=n).astype(dtype)


def sample_bounded(n, dtype, rng, bound):
    """Uniform magnitude within +/-bound -- for functions whose result
    overflows well inside the full finite float range (exp family), where
    sampling out to fmax just produces meaningless inf-vs-inf comparisons
    (and, worse, makes the mpmath reference computation itself blow up)."""
    return rng.uniform(-bound, bound, size=n).astype(dtype)


def sample_moderate(n, dtype, rng, bound=30.0):
    """Bounded magnitude -- for functions (erf/erfc) that saturate to their
    asymptote well inside the full finite range; sampling out to fmax just
    makes the mpmath reference computation blow up for no test value."""
    return rng.uniform(-bound, bound, size=n).astype(dtype)


def sample_gamma_domain(n, dtype, rng):
    """tgamma: positive, bounded below the double-precision overflow point
    (~171.6) so both PoCL and the mpmath reference stay finite."""
    return np.exp(rng.uniform(np.log(1e-3), np.log(170.0), size=n)).astype(dtype)


def sample_small_int(n, rng, lo=-8, hi=8):
    vals = rng.integers(lo, hi + 1, size=n)
    vals[vals == 0] = 1  # avoid degenerate x**0 dominating the sweep
    return vals.astype(np.int32)


def shuffled_lanes(samples, width, rng):
    """Trim to a multiple of width and shuffle so each width-wide chunk
    ('lane group') mixes independently-drawn magnitudes."""
    n = (len(samples) // width) * width
    samples = samples[:n].copy()
    rng.shuffle(samples)
    return samples


# --------------------------------------------------------------------------
# ULP error
# --------------------------------------------------------------------------

def ulp_error(computed, reference_mp, dtype):
    """Error in ULPs of `dtype`, as a (possibly fractional) multiple of the
    local float spacing at the reference value -- matches the fractional
    ULP figures in the original session logs."""
    ref_float = dtype(float(reference_mp))
    if not np.isfinite(ref_float):
        return 0.0 if not np.isfinite(computed) else float("inf")
    # both args to nextafter must share dtype -- passing a bare Python float
    # (np.inf) silently promotes a float32 ref_float to float64, computing
    # the spacing at the wrong precision (10^8-scale bogus ULP values).
    direction = dtype(np.inf) if ref_float >= 0 else dtype(-np.inf)
    nxt = np.nextafter(ref_float, direction)
    spacing = abs(float(nxt) - float(ref_float))
    if spacing == 0:
        spacing = float(np.finfo(dtype).tiny)
    diff = abs(mpmath.mpf(float(computed)) - reference_mp)
    return float(diff / mpmath.mpf(spacing))


# --------------------------------------------------------------------------
# Device / kernel execution
# --------------------------------------------------------------------------

def get_pocl_context():
    for plat in cl.get_platforms():
        if "portable computing language" in plat.name.lower() or "pocl" in plat.name.lower():
            devs = plat.get_devices()
            ctx = cl.Context(devices=devs)
            return ctx, devs[0]
    # fall back to whatever's first (single-platform containers)
    ctx = cl.create_some_context(interactive=False)
    return ctx, ctx.devices[0]


def device_supports_denormals(dev, precision):
    from pyopencl import device_fp_config as fp
    cfg = dev.single_fp_config if precision == "float" else dev.double_fp_config
    try:
        return bool(cfg & fp.DENORM)
    except Exception:
        return False


def vload_kernel(fn_cl_name, width, cl_type, arity, int_arg_index=None):
    """Generate an OpenCL C kernel that reads `arity` operands (width-wide,
    via vloadN/vstoreN to sidestep vec3 padding) and writes fn(operands)."""
    if width == 1:
        loads = "\n    ".join(f"{cl_type} a{k} = in{k}[i];" for k in range(arity))
        store = "out[i] = "
        end = ";"
    else:
        vt = f"{cl_type}{width}"
        vload = "vload3" if width == 3 else f"vload{width}"
        vstore = "vstore3" if width == 3 else f"vstore{width}"
        loads = "\n    ".join(f"{vt} a{k} = {vload}(i, in{k});" for k in range(arity))
        store = f"{vt} r = "
        end = f";\n    {vstore}(r, i, out);"

    if int_arg_index is not None:
        # pown/rootn take an int operand matching the float operand's width
        # (pown(float4, int4)), not a scalar -- must vload it the same way.
        if width == 1:
            loads += "\n    int b = in_int[i];"
        else:
            ivload = "vload3" if width == 3 else f"vload{width}"
            loads += f"\n    int{width} b = {ivload}(i, in_int);"
        args = ", ".join([f"a{k}" for k in range(arity)] + ["b"])
    else:
        args = ", ".join(f"a{k}" for k in range(arity))

    int_param = ", __global const int* in_int" if int_arg_index is not None else ""
    in_params = ", ".join(f"__global const {cl_type}* in{k}" for k in range(arity))

    return f"""
__kernel void sweep(
    {in_params}{int_param},
    __global {cl_type}* out)
{{
    int i = get_global_id(0);
    {loads}
    {store}{fn_cl_name}({args}){end}
}}
"""


def run_kernel(ctx, dev, src, buffers_in, n_vectors, width, cl_type, out_dtype, int_buf=None):
    prg = cl.Program(ctx, src).build()
    queue = cl.CommandQueue(ctx, dev)
    mf = cl.mem_flags
    bufs = [cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b) for b in buffers_in]
    kwargs = {}
    args = list(bufs)
    if int_buf is not None:
        int_cl = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=int_buf)
        args.append(int_cl)
    out_len = n_vectors * width
    out_host = np.empty(out_len, dtype=out_dtype)
    out_cl = cl.Buffer(ctx, mf.WRITE_ONLY, out_host.nbytes)
    args.append(out_cl)
    prg.sweep(queue, (n_vectors,), None, *args)
    cl.enqueue_copy(queue, out_host, out_cl)
    queue.finish()
    return out_host
