---
description: "CodeRabbit, ponytail-review and the gate-integrity scan report on the branch, the main loop clusters by root cause and decides, one agent per cluster fixes correctness only, gates run, three-section report"
argument-hint: "base ref, then optional free text naming what to watch for"
disable-model-invocation: true
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git merge-base:*), Bash(git status:*), Bash(python3 ~/.claude/scripts/gate-scan.py:*)
---

Base ref argument: $ARGUMENTS
Current branch: !`git branch --show-current`

`/jun-review → ask base → 2 reviewers + gate scan report → main loop clusters and decides → one agent per cluster → gates → report`

You orchestrate. Reviewers only report, verbatim. You decide per cluster. Every edit ships through a dispatched agent that carries the full context.

## 0. Base and focus

The first word of the argument above is the base ref; everything after it is the focus, free text naming what to watch for (a file, a flow, a worry). If the base is empty, ask with AskUserQuestion: `main` (Recommended), `development`, or another ref. Never guess. Both reviewers get the same base. Uncommitted changes are in scope.

Focus narrows attention, never scope. Each reviewer prompt in §1 carries it as: "Look hardest at <focus>. Still report everything."

## 1. Gather (report only)

Run all three in one message:

1. **CodeRabbit**: Agent `coderabbit:code-reviewer` with `model: sonnet`, `effort: high`. Prompt: review the diff from `<base>` to the working tree and return **every** finding, none merged or dropped, as `file:line · severity · claim · failure scenario or none · suggested fix`, plus the count the CLI reported so you can check nothing was lost. It must not edit.
2. **ponytail-review**: Agent `deep` (opus, high). Prompt: invoke the `ponytail:ponytail-review` skill on the diff from `<base>` to the working tree and return its report in full. It must not edit; return the report only.
3. **Gate scan**: `python3 ~/.claude/scripts/gate-scan.py <base>`. Read-only; it lists added lines that weaken a gate (test removed or skipped, snapshot changed without its owner, suppression, CI bypass, relaxed timeout or threshold, placeholder, env sniffing, swallowed exception) and never judges them. A non-zero exit or a `GATE_ERROR` line means the scan is **UNAVAILABLE**; carry that word into §5 and never write "none" for it.

Normalise every reviewer finding to one shape: `file:line`, source (`coderabbit:<severity>` / `ponytail:<group>`), claim, consequence, failure scenario or `none`. Gate-scan lines keep their own shape (`RH-n path:line + text`) and skip §2 clustering; they go straight to the gate-integrity read below.

## 2. Interpret (this loop, no delegation)

Cluster by mechanism, not by line. One root cause reported twice is one cluster, fixed once at the right depth. Rank by consequence. With a focus, clusters touching the focus rank first and are tagged `focus`; the rest follow unchanged.

Every finding is a claim. Read the code before a severe one earns a fix; drop false positives and say so.

Fix a cluster only when it is **correctness**: a reviewer named a failure scenario and you reproduced it against the code, or it is a never-cut item (validation at a trust boundary, error handling that prevents data loss, security, accessibility), or it is the gate restore named below. Everything else is optional, default no, with one line `If left:` or `cosmetic`.

Scope: edit only files in `git diff --name-only <base>...HEAD` plus uncommitted changes, and the test co-located with one of them. Anything else is an own-branch follow-up. A shared helper outside the diff is reported, not patched at the caller.

**Gate integrity.** For every line the scan tagged, open the hunk and write one line stating what it does: silences the failure the gate was there to catch, or is justified by something visible in this diff (the case is now covered elsewhere, the threshold moved with a measurement). That line is a reading, never a pick. Except for the removed-test case, a tagged line is not fixed by a dispatched agent in §3 and is never dropped silently: every one lands in §5 section 2 with its tag, `path:line`, the reading, and the options restore / keep, justified / leave open. A removed test whose function survived is a plainly accidental loss: a `patch` restores it, named in section 1 as a gate restore.

## 3. Fix (one agent per cluster)

Dispatch one agent per independent cluster: `patch` for a single-site cluster (one or two files, exact change), `builder` for the rest, all in a single message so they run concurrently; sequence only where one fix depends on another. Each dispatch carries: the cluster's findings verbatim with consequences, the `file:line` sites, the relevant diff excerpt, the base ref, the allowlist of files it may edit (stop and report rather than touch anything else), the rule that the fix must not change behaviour beyond what the finding names, and an acceptance criterion it can check itself. Smallest change that closes the scenario.

A failed builder gets one fresh `deep` brief with the files kept and the conversation dropped; a failed `deep` is reported open with the gate's last lines. Never "fix it" to the same agent. Treat agent reports as claims: say which you verified.

## 4. Verify

Run the typecheck, lint and test scripts the repo's instructions or `package.json` name; a gate the repo does not define is reported as not run. A failing gate is reported with its last 15 lines, not chased into another fix round. Then re-run the CodeRabbit agent once on the same base, and the gate scan; anything still open is reported, and a tag new since §1 is reported as introduced by a fix.

## 5. Report

Open with `Fixed <n> · To decide <n> · Later <n>`. Then exactly three sections:

1. **Done — read, then commit.** One line per fix. A `focus`-tagged line says so.
2. **Yours to decide before commit.** Only blockers: failing gate, behaviour choice, open cluster, every gate-integrity tag. Each: Problem / What you'd see / Options. No Recommend line. A gate-integrity item uses the tag as its title, its reading as the Problem, and the options restore / keep, justified / leave open. End the section with: "Pick per item, with a one-line why." Your own view on each item comes only in the reply to their picks: agree or differ, plus what the reason missed. A bare option label gets one "and why?"; "just do it" after that proceeds and the reply says the pick was waved.
3. **Later — read once.** Two lists: "Has a consequence" (`<finding> — If left: <…>`) and "Cosmetic". Not a to-do.

Close with a gate table (name, pass/fail) whose last row is `Gate integrity: none tagged` / `<n> tagged, see 2` / `UNAVAILABLE (<reason>)`, and: "Read 1, then 2, then stop."
