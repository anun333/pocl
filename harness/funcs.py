"""
Function table for the ULP sweep. `bound` values are the OpenCL 1.2/3.0 full
profile max-error requirements (embedded profile is looser) where the spec
defines one; where the recovered session notes call out a tighter observed
bound for a specific build (e.g. "exp full 0.99/0.94 ULP" against a bound of
2, or log1p denied at bound 2-3), that tighter figure is used instead so the
sweep matches what the original series was actually gated on.
"""
from functools import partial

from . import common as C

# exp-family functions overflow to +-inf well inside the full finite double
# range (exp() past ~709.8, exp2() past ~1024, exp10() past ~308); sampling
# the whole finite range makes the mpmath reference computation itself blow
# up on astronomically large exponents for no useful signal, so these get
# bounded domains instead of sample_any.
_exp_dom = partial(C.sample_bounded, bound=700.0)
_exp2_dom = partial(C.sample_bounded, bound=1000.0)
_exp10_dom = partial(C.sample_bounded, bound=300.0)

# (name, cl_name, arity, domain_fn, mp_fn, bound)
# arity: 1 = unary, 2 = binary float, 'i' suffix = second arg is int (pown/rootn)
UNARY = [
    ("sin", "sin", C.sample_periodic, lambda x: __import__("mpmath").sin(x), 4.0),
    ("cos", "cos", C.sample_periodic, lambda x: __import__("mpmath").cos(x), 4.0),
    ("tan", "tan", C.sample_periodic, lambda x: __import__("mpmath").tan(x), 5.0),
    ("exp", "exp", _exp_dom, lambda x: __import__("mpmath").exp(x), 2.0),
    ("exp2", "exp2", _exp2_dom, lambda x: __import__("mpmath").power(2, x), 3.0),
    ("exp10", "exp10", _exp10_dom, lambda x: __import__("mpmath").power(10, x), 3.0),
    ("expm1", "expm1", _exp_dom, lambda x: __import__("mpmath").expm1(x), 3.0),
    ("log", "log", C.sample_positive, lambda x: __import__("mpmath").log(x), 3.0),
    ("log2", "log2", C.sample_positive, lambda x: __import__("mpmath").log(x, 2), 3.0),
    ("log10", "log10", C.sample_positive, lambda x: __import__("mpmath").log10(x), 3.0),
    ("log1p", "log1p", C.sample_gt_neg1, lambda x: __import__("mpmath").log1p(x), 2.0),
    ("cbrt", "cbrt", C.sample_any,
     lambda x: __import__("mpmath").sign(x) * __import__("mpmath").power(abs(x), __import__("mpmath").mpf(1) / 3),
     2.0),
    ("sqrt", "sqrt", C.sample_positive, lambda x: __import__("mpmath").sqrt(x), 3.0),
    ("erf", "erf", C.sample_moderate, lambda x: __import__("mpmath").erf(x), 16.0),
    ("erfc", "erfc", C.sample_moderate, lambda x: __import__("mpmath").erfc(x), 16.0),
    ("tgamma", "tgamma", C.sample_gamma_domain, lambda x: __import__("mpmath").gamma(x), 16.0),
    ("asinh", "asinh", C.sample_any, lambda x: __import__("mpmath").asinh(x), 4.0),
    ("acosh", "acosh", C.sample_ge1, lambda x: __import__("mpmath").acosh(x), 4.0),
    ("atanh", "atanh", C.sample_pm1, lambda x: __import__("mpmath").atanh(x), 5.0),
]

_pow_exp_dom = partial(C.sample_bounded, bound=20.0)

BINARY = [
    ("pow", "pow", C.sample_positive, _pow_exp_dom,
     lambda x, y: __import__("mpmath").power(x, y), 16.0),
    ("hypot", "hypot", C.sample_any, C.sample_any,
     lambda x, y: __import__("mpmath").hypot(x, y), 2.0),
    ("atan2", "atan2", C.sample_any, C.sample_any,
     lambda x, y: __import__("mpmath").atan2(x, y), 6.0),
]

# pown(float, int) / powr(float, float) / rootn(float, int) -- the direct
# subject of PR #2307/#2311's deny-list work.
INT_ARG = [
    ("pown", "pown", C.sample_positive, lambda x, n: __import__("mpmath").power(x, n), 16.0),
    ("rootn", "rootn", C.sample_positive, lambda x, n: __import__("mpmath").root(x, n), 16.0),
]

POWR = [
    ("powr", "powr", C.sample_positive, _pow_exp_dom,
     lambda x, y: __import__("mpmath").power(x, y), 16.0),
]

ALL_NAMES = (
    [f[0] for f in UNARY] + [f[0] for f in BINARY]
    + [f[0] for f in INT_ARG] + [f[0] for f in POWR]
)
