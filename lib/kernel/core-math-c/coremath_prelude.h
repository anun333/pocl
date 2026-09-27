/* Included ahead of each of CORE-MATH's C files when they are compiled into
   the kernel library (lib/kernel/host/CMakeLists.txt), so that the files
   themselves stay verbatim.

   - CORE-MATH tags some NaNs, as in __builtin_nanf("<0"). Clang folds
     __builtin_nan only for an empty or numeric tag, and otherwise emits a
     call to nanf, which the kernel library does not have. glibc answers
     every such tag with the default NaN, which is what __builtin_nanf("")
     folds to, so the tag is dropped here.
   - lgamma also writes the sign to libc's global signgam, which OpenCL's
     lgamma does not return and every work-item would race on: each write
     goes to a fresh automatic object instead.

   Copyright (c) 2026 anun333
   MIT license, as the rest of PoCL. */

#define __builtin_nanf(tag) __builtin_nanf ("")
#define __builtin_nan(tag) __builtin_nan ("")
#define signgam (*(int[1]){ 0 })
