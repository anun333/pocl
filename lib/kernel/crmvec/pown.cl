/* OpenCL built-in library: pown() from crmvec (see crmvec.h) */
#include "crmvec.h"

float __crm_pownf (float, int) __asm__ ("crmvec_pownf") __attribute__ ((const));
float _CL_OVERLOADABLE pown (float a, int b) { return __crm_pownf (a, b); }
float2 _CL_OVERLOADABLE pown (float2 a, int2 b) { return (float2) (pown (a.s0, b.s0), pown (a.s1, b.s1)); }
float3 _CL_OVERLOADABLE pown (float3 a, int3 b) { return (float3) (pown (a.s01, b.s01), pown (a.s2, b.s2)); }
float4 _CL_OVERLOADABLE pown (float4 a, int4 b) { return (float4) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }
float8 _CL_OVERLOADABLE pown (float8 a, int8 b) { return (float8) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }
float16 _CL_OVERLOADABLE pown (float16 a, int16 b) { return (float16) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }

#ifdef cl_khr_fp64
double __crm_pown (double, int) __asm__ ("crmvec_pown") __attribute__ ((const));
double _CL_OVERLOADABLE pown (double a, int b) { return __crm_pown (a, b); }
double2 _CL_OVERLOADABLE pown (double2 a, int2 b) { return (double2) (pown (a.s0, b.s0), pown (a.s1, b.s1)); }
double3 _CL_OVERLOADABLE pown (double3 a, int3 b) { return (double3) (pown (a.s01, b.s01), pown (a.s2, b.s2)); }
double4 _CL_OVERLOADABLE pown (double4 a, int4 b) { return (double4) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }
double8 _CL_OVERLOADABLE pown (double8 a, int8 b) { return (double8) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }
double16 _CL_OVERLOADABLE pown (double16 a, int16 b) { return (double16) (pown (a.lo, b.lo), pown (a.hi, b.hi)); }
#endif
