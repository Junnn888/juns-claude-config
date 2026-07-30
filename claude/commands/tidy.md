---
description: "Fork of the built-in /simplify with a fifth angle for self-explanatory code. Review the changed code for reuse, simplification, efficiency, altitude, and self-explanation cleanups, then apply the fixes. Quality only — it does not hunt for bugs; use /code-review for that."
argument-hint: "[<target>]"
---

Review target: $ARGUMENTS

`/tidy → 5 cleanup agents in parallel → apply the fixes`

You are improving the quality of the changed code, not hunting for bugs. Review
it for reuse, simplification, efficiency, altitude, and self-explanation issues,
then fix what you find. Do not look for correctness bugs — that is what `/code-review` is
for.

## Phase 0 — Gather the diff

Run `git diff @{upstream}...HEAD` (or `git diff main...HEAD` / `git diff HEAD~1`
if there's no upstream) to get the unified diff under review. If there are
uncommitted changes, or the range diff is empty, also run `git diff HEAD` and
include the working-tree changes in scope — the review often runs before the
commit. If a PR number, branch name, or file path was passed as the review
target above, review that target instead. Treat this diff as the review scope.

## Phase 1 — Review (5 cleanup agents in parallel)

Launch **5 independent review agents** via the Agent tool, all in a single
message so they run concurrently. Pass each agent the diff and one of the five
angles below. Each returns its findings with `file`, `line`, a one-line
`summary`, and the concrete cost (what is duplicated, wasted, or harder to
maintain). If the Agent tool is unavailable in this context, work through all
five angles yourself in one pass — do not skip an angle for lack of fan-out,
and say in the summary that the review was single-pass.

### Reuse

Flag new code that re-implements something the codebase
already has — Grep shared/utility modules and files adjacent to the change,
and name the existing helper to call instead.

### Simplification

Flag unnecessary complexity the diff adds: redundant or derivable state,
copy-paste with slight variation, deep nesting, dead code left behind. Name
the simpler form that does the same job.

### Efficiency

Flag wasted work the diff introduces: redundant computation or repeated I/O,
independent operations run sequentially, blocking work added to startup or
hot paths. Also flag long-lived objects built from closures or captured
environments — they keep the entire enclosing scope alive for the object's
lifetime (a memory leak when that scope holds large values); prefer a
class/struct that copies only the fields it needs. Name the cheaper
alternative.

### Altitude

Check that each change is implemented at the right depth, not as a fragile
bandaid. Special cases layered on shared infrastructure are a sign the fix
isn't deep enough — prefer generalizing the underlying mechanism over adding
special cases.

### Self-explanatory code

Treat every explanatory comment in the diff as a signal that the code does not
explain itself. The preferred fix is to restructure until the comment has
nothing left to say — rename the variable or function to state what the
comment stated, extract a well-named function or predicate, replace the clever
expression with a plain one — then delete the comment. Deletion alone is right
only for comments with no information to fold back in: restatements of the
code, narration of the change ("now uses X", "moved from Y"), commented-out
code, and comments the change made stale.

A comment earns its place only when its rationale is non-recoverable from any
shape of the code: an upstream-bug workaround, a non-obvious invariant, a
ticket link. Keep those as a one-line why — and flag the inverse, a spot where
such a why is missing. Judge against the surrounding file's comment density
and idiom, and leave comments the diff didn't touch alone.

## Phase 2 — Apply the fixes

Wait for all five agents to complete, dedup findings that point at the same
line or mechanism, and fix each remaining one directly. Skip any finding whose
fix would change intended behavior, require changes well outside the reviewed
diff, or that you judge to be a false positive — note the skip rather than
arguing with it. Finish with a brief summary of what was fixed and what was
skipped (or confirm the code was already clean).
