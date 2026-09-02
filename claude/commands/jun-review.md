---
description: "Run /blast-radius, /tidy and CodeRabbit as findings-only reviewers, interpret the three sets together in the main loop, then eliminate each root cause with one targeted agent"
argument-hint: "[<base ref>]"
---

Base ref: $ARGUMENTS

`/jun-review → 3 reviewers gather findings → main loop clusters by root cause → one fix wave`

You are the orchestrator for this review. The three reviewers only report. You
interpret their findings side by side, decide what each root cause needs, and
dispatch the fixes. No reviewer applies a fix, and you do not fix anything
yourself — every edit ships through a targeted agent that has the full context.

## Phase 0 — Scope

Detect the base once: the argument above if given, else `origin/development`
if it exists, else `origin/main`, else `main`. State which you picked. Every
reviewer gets this same base so all three see the same diff. Uncommitted
changes are in scope — the review usually runs before the commit.

## Phase 1 — Gather (reviewers report, nobody fixes)

1. **CodeRabbit first, in the background.** Check `coderabbit --version` and
   `coderabbit auth status`. If it is missing or unauthenticated, say so and
   carry on with the other two — do not block the review on it. Otherwise run
   `coderabbit review --agent --base <base>` with `run_in_background` so it
   works while the other reviewers run. The CLI sends the diff to CodeRabbit's
   API: stop and say so if the diff contains secrets.
2. **`/blast-radius <base>`** via the Skill tool. It is already report-only.
   Keep its verdict table and its paste-ready PR-body block for the final report.
3. **`/tidy`** via the Skill tool, with the same base as its target — but stop
   after its Phase 1. Collect the five angles' findings and do not enter its
   Phase 2; the apply step belongs to this command, not to `/tidy`.
4. Collect the CodeRabbit output when it lands.

Normalise every finding to one shape: `file:line`, source
(`blast-radius` / `tidy:<angle>` / `coderabbit:<severity>`), one-line claim,
and the concrete consequence.

## Phase 2 — Interpret (main loop, no delegation)

This phase is the reason the command exists. Merge the three sets and cluster
by mechanism, not by line: one root cause reported three ways — a blast-radius
blind spot, a tidy altitude flag, and a CodeRabbit warning on the same shape —
is one cluster with one fix, made once at the right depth. Rank clusters by
consequence, not by how interesting the code is.

Every finding is a claim, not a result. Spot-check anything severe against the
code before it earns a dispatch; drop false positives and note them. Decide
per cluster: fix or skip. Skip only when the fix would change intended
behaviour (that is the user's call — surface it) or the finding is judged
false. "Outside the diff" is not a reason to skip: blast-radius findings live
in files the diff never touched, by construction.

## Phase 3 — Eliminate (one wave)

One agent per independent cluster, all dispatched in a single message so they
run concurrently. Sequence only where one cluster's fix genuinely depends on
another's. Tier by what makes the fix fail: `patch` when the whole change fits
in the dispatch prompt, `builder` for anything larger, `deep` only where the
cluster needs judgement rather than execution.

The agent starts blind, so each dispatch carries the full context: the
findings verbatim with their consequence sentences, the `file:line` sites, the
relevant diff excerpt, the base ref, the constraint that the fix must not
change behaviour beyond what the finding names, and an acceptance criterion
the agent can check itself.

## Phase 4 — Verify and report

Run the project's tests, typecheck and lint where they exist. Re-run
`coderabbit review --agent --base <base>` once to confirm the fixes landed —
no loop; anything still open is reported, not chased. Treat the agents'
reports as claims: say which parts you verified yourself.

Report exactly: clusters fixed with files changed, clusters skipped with the
reason, findings still open, validation run, and the blast-radius PR-body
block for the PR description.
