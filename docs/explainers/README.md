# Plain-language explainers

The technical docs in this repo (`harness/gap_analysis.md`, `RECOVERY.md`,
the root `README.md`) are written for someone already inside the problem.

These explainers are the other layer: the same work, explained from the
ground up, so the reasoning can be understood and defended by someone who
didn't do it — including future-you.

This is the start of the **versioned structural outline of the math and
logic** for these repos: written down, in git, moving with the code rather
than living in a chat log that disappears.

Rules of thumb for anything added here:

- Assume a smart reader with no background in the specific subsystem.
- Explain the *why*, not just the *what* — the decisions are the part
  that's hard to reconstruct later.
- Include the wrong turns. A recorded mistake is often more useful than a
  clean conclusion, because it tells you which way the trap door swings.
- Write it so it can be used to answer a hostile question honestly.

## Contents

- [llvm-vecfuncs-patch.md](llvm-vecfuncs-patch.md) — what
  [llvm/llvm-project#223817](https://github.com/llvm/llvm-project/pull/223817)
  does, the naming scheme it uses, and the reasoning behind every judgment
  call in it.
