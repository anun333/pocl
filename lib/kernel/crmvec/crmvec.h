/* OpenCL built-in library: builtins answered by crmvec (experimental,
   ENABLE_HOST_CPU_VECTORIZE_CRMVEC).

   Each builtin calls crmvec's scalar function by its exported name
   (crmvec_<name>), declared const so that the loop vectorizer may replace
   the call with crmvec's vector entry point (pocl_llvm_wg.cc,
   buildCrmvecRows). A call the vectorizer leaves alone reaches the scalar
   export itself. Both are correctly rounded. Needs crmvec's libmvec.so.1 at
   run time. Half overloads are not defined here (core-math/).

   Copyright (c) 2026 anun333
   MIT license, as the rest of PoCL. */

#include "../templates.h"

#define CRM_V_V(N)                                                             \
  float __crm_##N##f (float) __asm__ ("crmvec_" #N "f") __attribute__ ((const)); \
  float _CL_OVERLOADABLE N (float a) { return __crm_##N##f (a); }             \
  IMPLEMENT_BUILTIN_V_V (N, float2, NAME1_2 (__crm_##N##f))                   \
  IMPLEMENT_BUILTIN_V_V (N, float3, NAME1_3 (__crm_##N##f))                   \
  IMPLEMENT_BUILTIN_V_V (N, float4, NAME1_4 (__crm_##N##f))                   \
  IMPLEMENT_BUILTIN_V_V (N, float8, NAME1_8 (__crm_##N##f))                   \
  IMPLEMENT_BUILTIN_V_V (N, float16, NAME1_16 (__crm_##N##f))                 \
  __IF_FP64 (                                                                 \
  double __crm_##N (double) __asm__ ("crmvec_" #N) __attribute__ ((const));   \
  double _CL_OVERLOADABLE N (double a) { return __crm_##N (a); }              \
  IMPLEMENT_BUILTIN_V_V (N, double2, NAME1_2 (__crm_##N))                     \
  IMPLEMENT_BUILTIN_V_V (N, double3, NAME1_3 (__crm_##N))                     \
  IMPLEMENT_BUILTIN_V_V (N, double4, NAME1_4 (__crm_##N))                     \
  IMPLEMENT_BUILTIN_V_V (N, double8, NAME1_8 (__crm_##N))                     \
  IMPLEMENT_BUILTIN_V_V (N, double16, NAME1_16 (__crm_##N)))

#define CRM_V_VV(N)                                                            \
  float __crm_##N##f (float, float) __asm__ ("crmvec_" #N "f") __attribute__ ((const)); \
  float _CL_OVERLOADABLE N (float a, float b) { return __crm_##N##f (a, b); } \
  IMPLEMENT_BUILTIN_V_VV (N, float2, NAME2_2 (__crm_##N##f))                  \
  IMPLEMENT_BUILTIN_V_VV (N, float3, NAME2_3 (__crm_##N##f))                  \
  IMPLEMENT_BUILTIN_V_VV (N, float4, NAME2_4 (__crm_##N##f))                  \
  IMPLEMENT_BUILTIN_V_VV (N, float8, NAME2_8 (__crm_##N##f))                  \
  IMPLEMENT_BUILTIN_V_VV (N, float16, NAME2_16 (__crm_##N##f))                \
  __IF_FP64 (                                                                 \
  double __crm_##N (double, double) __asm__ ("crmvec_" #N) __attribute__ ((const)); \
  double _CL_OVERLOADABLE N (double a, double b) { return __crm_##N (a, b); } \
  IMPLEMENT_BUILTIN_V_VV (N, double2, NAME2_2 (__crm_##N))                    \
  IMPLEMENT_BUILTIN_V_VV (N, double3, NAME2_3 (__crm_##N))                    \
  IMPLEMENT_BUILTIN_V_VV (N, double4, NAME2_4 (__crm_##N))                    \
  IMPLEMENT_BUILTIN_V_VV (N, double8, NAME2_8 (__crm_##N))                    \
  IMPLEMENT_BUILTIN_V_VV (N, double16, NAME2_16 (__crm_##N)))
