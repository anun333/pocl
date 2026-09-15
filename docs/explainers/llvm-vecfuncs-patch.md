# What the LLVM patch does, in plain language

**Patch:** [llvm/llvm-project#223817](https://github.com/llvm/llvm-project/pull/223817)
**Written so you can answer review questions honestly.** If a reviewer asks
something not covered here, "I don't know, let me check" is a completely
normal and respected answer in code review. Guessing is worse.

---

## 1. The background idea: doing math 4 at a time

An ordinary CPU instruction does one calculation: `cos(x)` gives you one
answer.

Modern CPUs can also do the same operation to several numbers at once with
a single instruction — 2, 4, 8, sometimes 16 numbers simultaneously. Think
of a supermarket scanner that reads four items in one pass instead of one.
This is called **vectorization**, and it's a big speed win for anything
doing lots of repetitive math.

## 2. glibc ships fast "several at a time" math functions

On Linux, the standard C library (**glibc**) includes a companion library
called **libmvec** — "math, vectorized". It contains versions of `cos`,
`exp`, `log` and friends that compute 4 answers at once instead of 1.

They're already installed on your machine. Right now. Sitting there.

## 3. The compiler needs a phone book to find them

For the compiler (LLVM/Clang) to actually *use* those fast versions, it has
to know they exist and what they're called. It keeps a hardcoded lookup
table — a phone book — that says things like:

> "If you see code calling `cos`, and you're doing 4 at a time, call
> `_ZGVdN4v_cos` instead."

That phone book is the file `VecFuncs.def`.

## 4. The problem: the phone book is out of date

glibc **2.35** (released 2022) added vector versions of a bunch more
functions — `acos`, `atan2`, `tanh`, `log2`, `exp2`, `hypot` and others.

Nobody added them to LLVM's phone book for x86 computers.

So: the fast versions exist on your machine, the compiler is willing to use
fast versions, but it doesn't know their names, so it doesn't call them.
It falls back to doing them one at a time.

**The patch adds the missing phone book entries.** That's the whole idea.
48 lines. No logic changes, no new algorithms — just telling the compiler
about functions that already exist.

---

## 5. Decoding those ugly names

`_ZGVbN2v_acos` looks like line noise. It's actually a strict standard
naming scheme, and each piece means something:

| Piece | Meaning |
|---|---|
| `_ZGV` | marker: "this is a vector version of a function" |
| `b` | which CPU instruction set it needs (see below) |
| `N` | "no mask" — a variant we don't use here |
| `2` | how many numbers it handles at once |
| `v` | it takes one vector argument (`vv` = two arguments, like `hypot(a,b)`) |
| `_acos` | which function it is |

So `_ZGVbN2v_acos` = "the SSE2 version of acos that does 2 doubles at once."

The letter for instruction set:

| Letter | CPU feature | Register size | Doubles at once |
|---|---|---|---|
| `b` | SSE2 | 128-bit | 2 |
| `c` | AVX | 256-bit | 4 |
| `d` | AVX2 | 256-bit | 4 |
| `e` | AVX-512 | 512-bit | 8 |

---

## 6. Questions a reviewer might actually ask

### "Why did you only add `b` and `d`? glibc has four versions."

Because that's what LLVM's existing entries do. The `cos`, `exp`, `log`,
`pow`, `sin`, `tan` entries that were already in the file list only `b` and
`d` — `c` and `e` appear nowhere in the x86 section.

I followed the existing convention rather than changing it. `c` is
basically redundant with `d` (same width, `d` is the newer instruction
set), and whatever reason LLVM has for not listing `e`/AVX-512, that
decision predates this patch.

**Honest answer if pushed:** "I matched the existing convention. If you'd
like `c` and `e` added too, I can do that — I just didn't want to change
an existing policy in a patch that's meant to only fill a gap."

### "How do you know these functions actually exist?"

Ran a tool called `nm` on the actual library file on disk. It lists
everything a library provides. All 48 were there, and each was tagged
`@@GLIBC_2.35` — confirming they arrived in exactly the glibc version
claimed.

**There's a wrinkle worth knowing**, because it's the kind of thing a
reviewer might probe: glibc hides three of the four versions behind a
mechanism called **IFUNC**. That's a trick where the library picks the best
version for your specific CPU when the program starts. IFUNC entries show
up in the listing with a different marker than ordinary functions.

My first attempt filtered those out by accident and produced a wrong
conclusion (I thought only the `c` version existed). I caught it, redid
it, and the corrected analysis is what the patch is built on. This is
written down in `harness/gap_analysis.md` too.

### "How do you know the entries are *correct*, not just that the names exist?"

Wrote a small C program that calls each function directly through the exact
calling convention written in the patch, with known inputs, and compared
against the ordinary one-at-a-time answers.

All matched exactly. For example:
- `hypot(3,4)` → 5, and `hypot(5,12)` → 13 (the classic right triangles)
- `log2(1, 8, 1024, 0.5)` → 0, 3, 10, −1
- `acos`, `tanhf`, `atan2f` all matched the scalar results digit for digit

Tested both instruction sets (`b` and `d`), both precisions (float and
double), and both shapes (one-argument like `acos`, two-argument like
`hypot`).

### "Why did you leave out `sincos`?"

`sincos` is unusual: it gives you **two** answers from one call — the sine
*and* the cosine. In C it does that by writing into two memory locations
you hand it, rather than returning a value.

When you vectorize that, there are two possible conventions for those
output locations:

- **(a)** Hand it one starting address and say "put the results every 8
  bytes from here."
- **(b)** Hand it a whole vector of separate addresses, one per result.

Every other `sincos` entry in LLVM's file uses **(a)**. glibc's x86 version
uses **(b)**. And **(a)** is the shape LLVM's optimizer actually generates.

So an entry describing glibc's version-(b) would most likely never match
anything the compiler produces — dead weight at best. At worst, if it did
somehow match, the mismatch in how output addresses are interpreted could
write results to the wrong memory.

So I left it out and explained why in the PR, rather than adding an entry
that can't work.

**Honest answer if pushed:** "I think it needs a fix on the vectorizer
side, not a table row. But I may be wrong about that — if there's a way to
make it work, I'd like to know."

### "Did you use AI for this?"

Yes, and it's disclosed in the PR description per LLVM's AI Tool Use
Policy. The reasoning, the verification method, and the one wrong turn are
all written down in this repo (`harness/gap_analysis.md`) so the work can
be checked rather than taken on trust.

---

## 7. The short version, if you only remember one thing

> Your computer already has fast versions of about a dozen math functions.
> The compiler wasn't using them because its list of their names was out of
> date. This patch updates the list. I checked the names are real, and I
> checked the fast versions give the same answers as the slow ones.
