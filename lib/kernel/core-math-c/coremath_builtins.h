/* OpenCL built-in library: float and double builtins answered by CORE-MATH's
   correctly rounded C functions (experimental, ENABLE_HOST_CPU_COREMATH).

   cr_<name> and cr_<name>f come from CORE-MATH's own C files in this
   directory, compiled into the kernel library (lib/kernel/host/
   CMakeLists.txt), so no vector library is needed at run time. Vector
   overloads apply the scalar function lane by lane. Half overloads are not
   defined here (core-math/).

   Copyright (c) 2026 anun333
   MIT license, as the rest of PoCL. */

#include "../templates.h"

#define CM_V_V(N)                                                              \
  float cr_##N##f (float);                                                    \
  float _CL_OVERLOADABLE N (float a) { return cr_##N##f (a); }                \
  IMPLEMENT_BUILTIN_V_V (N, float2, NAME1_2 (cr_##N##f))                      \
  IMPLEMENT_BUILTIN_V_V (N, float3, NAME1_3 (cr_##N##f))                      \
  IMPLEMENT_BUILTIN_V_V (N, float4, NAME1_4 (cr_##N##f))                      \
  IMPLEMENT_BUILTIN_V_V (N, float8, NAME1_8 (cr_##N##f))                      \
  IMPLEMENT_BUILTIN_V_V (N, float16, NAME1_16 (cr_##N##f))                    \
  __IF_FP64 (                                                                 \
  double cr_##N (double);                                                     \
  double _CL_OVERLOADABLE N (double a) { return cr_##N (a); }                 \
  IMPLEMENT_BUILTIN_V_V (N, double2, NAME1_2 (cr_##N))                        \
  IMPLEMENT_BUILTIN_V_V (N, double3, NAME1_3 (cr_##N))                        \
  IMPLEMENT_BUILTIN_V_V (N, double4, NAME1_4 (cr_##N))                        \
  IMPLEMENT_BUILTIN_V_V (N, double8, NAME1_8 (cr_##N))                        \
  IMPLEMENT_BUILTIN_V_V (N, double16, NAME1_16 (cr_##N)))

#define CM_V_VV(N)                                                             \
  float cr_##N##f (float, float);                                             \
  float _CL_OVERLOADABLE N (float a, float b) { return cr_##N##f (a, b); }    \
  IMPLEMENT_BUILTIN_V_VV (N, float2, NAME2_2 (cr_##N##f))                     \
  IMPLEMENT_BUILTIN_V_VV (N, float3, NAME2_3 (cr_##N##f))                     \
  IMPLEMENT_BUILTIN_V_VV (N, float4, NAME2_4 (cr_##N##f))                     \
  IMPLEMENT_BUILTIN_V_VV (N, float8, NAME2_8 (cr_##N##f))                     \
  IMPLEMENT_BUILTIN_V_VV (N, float16, NAME2_16 (cr_##N##f))                   \
  __IF_FP64 (                                                                 \
  double cr_##N (double, double);                                             \
  double _CL_OVERLOADABLE N (double a, double b) { return cr_##N (a, b); }    \
  IMPLEMENT_BUILTIN_V_VV (N, double2, NAME2_2 (cr_##N))                       \
  IMPLEMENT_BUILTIN_V_VV (N, double3, NAME2_3 (cr_##N))                       \
  IMPLEMENT_BUILTIN_V_VV (N, double4, NAME2_4 (cr_##N))                       \
  IMPLEMENT_BUILTIN_V_VV (N, double8, NAME2_8 (cr_##N))                       \
  IMPLEMENT_BUILTIN_V_VV (N, double16, NAME2_16 (cr_##N)))
