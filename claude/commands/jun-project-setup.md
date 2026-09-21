---
description: "Survey a project's guardrails, propose what is missing, then register the project with the local lint kit — per-repo settings and a docs-first pointer, both outside the repository — and report the measured baseline"
argument-hint: "[<project path>]"
---

Project path: $ARGUMENTS

`/jun-project-setup → scout survey → gap table + proposal → approve → one builder writes local settings → report`

You are the orchestrator for this setup. The survey only reports; you read it,
decide what is worth reporting as a gap, and put the whole proposal in front of
the user before anything is written. Every write ships through one `builder` —
you do not edit yourself. **This command installs nothing into the repository.**
Everything it writes lives in `~/.claude/lint/` or in a git-excluded
`CLAUDE.local.md`, so it is safe in a repo you do not own. You never run a git
command, and you never install a dependency.

The rules themselves live in the local lint kit at `~/.claude/lint/`: max-lines
400, max-lines-per-function 80, complexity 12, max-params 4, max-depth 4,
sonarjs cognitive-complexity 15, and the Tailwind bracket ban. The kit reads
them from its own config, against this project's files, with no project config
involved.

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
   report exit code plus the last 15 lines. The Stop gate runs them when they
   exist. Hooks in `.claude/settings*.json` and CI workflows that run lint or
   typecheck.
2. **Kit state.** `~/.claude/lint/kit.sh installed` — exit code and any output.
   `~/.claude/lint/kit.sh paths` — the `settings=` and `snapshot=` paths for
   this work tree, and whether either file already exists.
3. **Rules the project already enforces itself.** Informational only, not gaps:
   which of `max-lines`, `max-lines-per-function`, `complexity`, `max-params`,
   `max-depth`, sonarjs cognitive-complexity and a Tailwind bracket restriction
   the project's own ESLint config sets, and TypeScript `strict`. Both the
   project's lint and the kit will run; overlap is duplicate reporting, not a
   conflict.
4. **Tailwind and styling.** Version, the CSS file carrying `@theme` (or the
   Tailwind config, whichever the project uses), the count of arbitrary bracket
   classes in source (`grep -rEo '\b[a-z-]+-\[[^]]+\]'` over the source dirs)
   with the ten most frequent patterns, and the count of `style={{`.
5. **Size.** The ten largest source files by line count, and how many exceed 300
   lines.
6. **Docs.** Total lines of the project `CLAUDE.md`, `AGENTS.md` and
   `.claude/rules/*.md`; and whether the project has a vault map — search the
   Tolaria MCP (`search_notes`) for `ux-flow-index` scoped to the project's
   vault folder, and read the project `CLAUDE.md` for a vault path.

## Phase 2 — Propose (main loop, no edits)

Print one gap table, a row per check — docs-first pointer, `lint` script,
`typecheck` script, kit installed, kit settings — with columns **Present?**,
**Measured** (the number the survey came back with) and **Action**.

The two script rows are report-only. This command no longer adds scripts to the
repository, so a missing one reads: "missing — the Stop gate will run the kit
only". The kit-settings row names the Tailwind entry path the survey found
(yes/no, plus the path) since that is the one value the settings file carries
beyond the project name.

If the kit is not installed, `kit.sh installed` prints the command to run. Pass
it to the user with the `!` prefix so it executes in this session and the output
lands in the conversation, and wait for it before Phase 3. Nothing else is
installed by this command.

Then, per step, the proposal: exactly what will be written and where. Stop there
and wait. The user may drop any step; only what they approve reaches Phase 3.

## Phase 3 — Apply (one `builder`)

Approved steps only. Add if missing, never overwrite an existing file — a value
already set is left alone and reported as already present. The builder starts
blind, so the dispatch carries the survey's `path:line` findings, the exact
`settings=` path from `kit.sh paths`, and the exact content to write.

1. **Kit settings.** Write the per-repo settings JSON at the `settings=` path:

   ```json
   {
     "name": "<repo dir name>",
     "tailwindEntry": "app/globals.css"
   }
   ```

   `tailwindEntry` is the CSS file containing `@theme`, else the Tailwind
   config, else `null` when the project uses neither — the kit's bracket ban
   only runs when it is set.
2. **Docs first.** Write this section to `CLAUDE.local.md` at the project root,
   filling `<vault folder>`, `<index note>` and `<branch>` from the survey, and
   append `CLAUDE.local.md` to `.git/info/exclude` if it is not already listed.
   Never write to a tracked `CLAUDE.md`. Skip with a note if the project has no
   map.

   ```markdown
   ## Docs first

   This codebase is mapped in the vault. Before exploring code for any question, task, or plan:

   1. Read `<vault folder>/<index note>` and pick the area doc(s) it points to.
   2. Read those area docs. They carry `file:line` footnotes; start from the files they name rather than searching.
   3. Only then open code, and only the areas the docs point to.

   Each doc's `verified_against` names the commit it was last checked against, on `<branch>`. When code and doc disagree, say so and treat the doc as possibly stale, not the code as wrong. Scout dispatches for this project name the relevant area doc(s) so the agent starts there too.
   ```
3. **Baseline.** Run `~/.claude/lint/kit.sh baseline` to take this work tree's
   suppressions snapshot — idempotent, so a re-run is safe — then
   `~/.claude/lint/kit.sh check` and confirm it exits 0. If it does not, the
   builder reports the failure and does not claim done.

## Phase 4 — Report

- Files written, one line each — all under `~/.claude/lint/projects/`, plus the
  project's `CLAUDE.local.md`.
- The explicit line: **No file in the repository was changed.**
- The measured baseline: bracket-class count and top patterns, inline-style
  count, files over 300 lines, and the number of violations in this work tree's
  snapshot.
- The hand-off: the Stop gate lints changed files against this work tree's
  snapshot; `/jun-review` runs the kit's duplication and dead-code checks; new
  work trees snapshot themselves at session start — nothing to run per work
  tree.
- Design decisions left to the user, stated as decisions rather than defects —
  e.g. "top pattern `text-[10px]` ×1007 — a missing type scale; naming it is a
  project decision".
- An offer to save the report as an Audit note in the project's vault folder,
  with `type: Audit`, `related_to: "[[<project>]]"` and `_width: wide`, so the
  numbers can be compared later and decay measured.

## Re-running

Run it once per repository, not per work tree — new work trees take their own
snapshot at session start.

A second run surveys again and skips everything already present. It only
rewrites the settings file when the Tailwind entry has moved.
