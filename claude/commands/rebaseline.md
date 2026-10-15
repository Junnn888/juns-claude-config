---
allowed-tools: Bash(~/.claude/lint/kit.sh:*)
description: "Re-take this worktree's lint-kit baselines: the ESLint snapshot, jscpd and knip, or only jscpd with `dupes`"
disable-model-invocation: true
argument-hint: "[dupes]"
---

## Kit output

!`~/.claude/lint/kit.sh baseline $ARGUMENTS`

## Instructions

The kit already ran above: no argument re-took the ESLint snapshot plus the
jscpd and knip baselines; `dupes` reset only the jscpd baseline.

Relay that output in one or two lines and nothing else. Run nothing, and do not
re-run the kit. Empty output means the kit no-oped because this is not a git
worktree with a `package.json` at its root; say so in one line.
