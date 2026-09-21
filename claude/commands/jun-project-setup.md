---
description: "Survey a project's guardrails, propose the gaps, then install the per-project rules the config expects — docs-first pointer, lint/typecheck scripts, size and complexity rules baselined to today's tree — and report what the user must install by hand"
argument-hint: "[<project path>]"
---

Project path: $ARGUMENTS

`/jun-project-setup → scout survey → gap table + proposal → approve → one builder applies → verify → report`

You are the orchestrator for this setup. The survey only reports; you read it,
decide which gaps are worth closing, and put the whole proposal in front of the
user before anything is written. Every edit ships through one `builder` — you do
not edit yourself, and no second writer touches the same files. You never run a
git command, and you never install a dependency: the safety hook blocks
dependency adds, so packages are reported as commands for the user to run.

## Phase 0 — Target

The project is the argument above if given, else the current working directory.
Confirm it is a git work tree and state the path you settled on.

Detect the package manager once, by lockfile: `bun.lock` or `bun.lockb` → bun,
`pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, else npm. Every command you report
later uses that manager.

If there is no `package.json`, stop. Say the stack is not covered by this
command — it is JS/TS only for now — and report what a manual setup for that
stack would need.

## Phase 1 — Survey (one `scout`, read-only)

One dispatch, nothing written. Ask for every answer with `path:line`:

1. **Scripts and gates.** The `package.json` scripts block; whether `lint` and
   `typecheck` exist and whether they pass — run each with a 120s timeout and
   report exit code plus the last 15 lines. Hooks in `.claude/settings*.json`
   and CI workflows that run lint or typecheck.
2. **ESLint.** Version (from the lockfile, else `npx eslint --version`) and the
   config file. Which of `max-lines`, `max-lines-per-function`, `complexity`,
   `max-params`, `max-depth`, sonarjs cognitive-complexity,
   `no-restricted-syntax`, a Tailwind ESLint plugin, `eslint-suppressions.json`,
   jscpd and knip are already present. TypeScript `strict`.
3. **Tailwind and styling.** Version, where the theme lives, the count of
   arbitrary bracket classes in source
   (`grep -rEo '\b[a-z-]+-\[[^]]+\]'` over the source dirs) with the ten most
   frequent patterns, and the count of `style={{`.
4. **Size.** The ten largest source files by line count, and how many exceed 300
   lines.
5. **Docs.** Total lines of the project `CLAUDE.md`, `AGENTS.md` and
   `.claude/rules/*.md`; whether the project `CLAUDE.md` is git-ignored
   (`git check-ignore`); and whether the project has a vault map — search the
   Tolaria MCP (`search_notes`) for `ux-flow-index` scoped to the project's
   vault folder, and read the project `CLAUDE.md` for a vault path.

## Phase 2 — Propose (main loop, no edits)

Print one gap table, a row per check — docs-first, lint script, typecheck
script, size/complexity rules, suppressions baseline, Tailwind bracket ban,
cognitive complexity, jscpd, knip — with columns **Present?**, **Measured** (the
number the survey came back with) and **Action** (`add now`, `needs install` or
`skip`, each with its why).

Then, per addable step, the proposal: exactly what will be written and where.
Stop there and wait. The user may drop any step; only what they approve reaches
Phase 3.

If the survey found any of the plugin-based checks missing —
`eslint-plugin-better-tailwindcss`, `eslint-plugin-sonarjs`, `jscpd`, `knip` —
the proposal ends with an install step: one line per missing package group,
each with a plain-English line of what it adds (the Tailwind plugin bans
arbitrary bracket values so the agent must use theme tokens; sonarjs measures
cognitive complexity, how hard a function is to read; jscpd finds duplicated
blocks; knip finds unused files, exports and dependencies). Print the exact
command for the detected manager, e.g. `bun add -d
eslint-plugin-better-tailwindcss eslint-plugin-sonarjs jscpd knip`, and ask the
user to run it with the `!` prefix so it executes in this session and the
output lands in the conversation. This command never installs a package
itself — dependency adds are the user's call and the safety hook blocks them.
Wait for the install output before Phase 3; if the user declines, drop the
plugin steps and continue with the rest.

## Phase 3 — Apply (one `builder`)

Approved steps only. Add if missing, never overwrite an existing config — a rule
or script the project already sets is left alone and reported as already
present. The builder starts blind, so the dispatch carries the survey's
`path:line` findings, the detected manager and ESLint version, and the exact
content to write.

1. **Docs first.** Insert this section into the project `CLAUDE.md`, filling
   `<vault folder>`, `<index note>` and `<branch>` from the survey. Skip with a
   note if the project has no map.

   ```markdown
   ## Docs first

   This codebase is mapped in the vault. Before exploring code for any question, task, or plan:

   1. Read `<vault folder>/<index note>` and pick the area doc(s) it points to.
   2. Read those area docs. They carry `file:line` footnotes; start from the files they name rather than searching.
   3. Only then open code, and only the areas the docs point to.

   Each doc's `verified_against` names the commit it was last checked against, on `<branch>`. When code and doc disagree, say so and treat the doc as possibly stale, not the code as wrong. Scout dispatches for this project name the relevant area doc(s) so the agent starts there too.
   ```
2. **Scripts.** Add `"lint": "eslint"` and `"typecheck": "tsc --noEmit"` where
   missing; the typecheck script only when `tsconfig.json` exists.
3. **Size and complexity rules.** ESLint core only, added as `error` to the
   existing flat config — or to `.eslintrc*` if that is what the project uses:
   `max-lines` 400 and `max-lines-per-function` 80, both with `skipBlankLines`
   and `skipComments` true; `complexity` 12; `max-params` 4; `max-depth` 4. The
   thresholds are starting points, safe to set because the baseline follows.
4. **Baseline.** On ESLint ≥ 9.24, run `<manager> run lint -- --suppress-all`
   (or `npx eslint . --suppress-all`) to write `eslint-suppressions.json`, then
   re-run lint and confirm it exits 0. On anything older, add the rules as
   `warn` instead and say why in the report.
5. **Verify.** Run lint and typecheck. Both exit 0 or the builder reports the
   failure and does not claim done.
6. **Plugin checks** (only when the packages are installed, whether just now
   or before the run). Tailwind: `eslint-plugin-better-tailwindcss` →
   `no-restricted-classes` with `restrict: ["\\[([^\\[\\]]*?)\\](?!:)"]`, the
   allowlist `data-[…]`, `aria-[…]`, `group-data-[…]`,
   `env(safe-area-inset…)`, `calc(…)`, `var(--…)` as exceptions, and a message
   naming the project's theme file. sonarjs `cognitive-complexity` 15 as
   `error`, then re-run the suppressions baseline so today's hits are
   recorded. A `.jscpd.json` with `failOnNewClones` and a baseline, a
   `knip.json`, and `lint:dupes` / `lint:dead` scripts. Then verify again.

## Phase 4 — Report

- Files changed, one line each.
- The measured baseline: bracket-class count and top patterns, inline-style
  count, files over 300 lines, and the suppressed-violation count from
  `eslint-suppressions.json`.
- Whether the project `CLAUDE.md` is git-ignored — if it is, say the docs-first
  pointer lives on this machine only.
- Any plugin check the user declined to install, with the one-line explanation
  and the install command, so it can be picked up on a later run.
- Design decisions left to the user, stated as decisions rather than defects —
  e.g. "top pattern `text-[10px]` ×1007 — a missing type scale; naming it is a
  project decision".
- An offer to save the report as an Audit note in the project's vault folder,
  with `type: Audit`, `related_to: "[[<project>]]"` and `_width: wide`, so the
  numbers can be compared later and decay measured.

## Re-running

The command is idempotent: a second run surveys again and skips everything
already present. That second run, after the user has installed the plugins, is
the intended path for the plugin-based checks — nothing here ever installs them.

A later run after a declined install picks the plugin checks up: the survey
finds the packages present and Phase 3 item 6 applies.
