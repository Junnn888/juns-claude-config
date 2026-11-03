---
description: "Set up a repo for interactive sessions: survey its instruction files, ask Tolaria or not, write a git-excluded CLAUDE.local.md at the root (copied from the main checkout inside a worktree), optionally register the project in the vault. Nothing tracked is touched."
argument-hint: "[<repo path>]"
disable-model-invocation: true
---

Repo path argument: $ARGUMENTS
Top level: !`git rev-parse --show-toplevel 2>/dev/null || echo NONE`
Common git dir: !`git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo NONE`
Exclude file: !`git rev-parse --path-format=absolute --git-path info/exclude 2>/dev/null || echo NONE`

`/jun-setup → detect → scan repo instructions → worktree copy, or first-run questions → announce and wait → one patch writes CLAUDE.local.md → report`

You orchestrate. The command installs nothing into the repository: the only file it writes inside the work tree is `CLAUDE.local.md`, listed in the git exclude file so it is never tracked. Every write inside the work tree goes through one `patch` dispatch; vault files are the main loop's own. You never run a git command that changes state, never install a dependency, never edit a tracked file.

## 0. Target

The repo is the argument above if given, else the top level shown. If it is `NONE`, stop: not a git work tree. The **main checkout** is the parent directory of the common git dir. This session is in a worktree when the top level differs from the main checkout.

## 1. Detect

Read, do not write:

- Root instruction files: `CLAUDE.md`, `AGENTS.md`, `CLAUDE.local.md` at the top level; whether `CLAUDE.md` is only an `@AGENTS.md` import.
- The main checkout's `CLAUDE.local.md`, if any, and its hash; the hash of the local one, if any.
- Whether the exclude file already lists `CLAUDE.local.md`.
- Whether the tolaria MCP is connected (`list_vaults` answers).

## 2. Scan the repo's instructions (report only)

Grep `CLAUDE.md` and `AGENTS.md` for instructions written for automation: `branch`, `rebase`, `push`, `pull request`, `PR`, `commit`, `merge`, `worktree`, `own your`, `do not ask`, `without asking`, `proceed`. Print the matching lines with their line numbers under one heading, then one sentence: in this session those lines describe the project; the global rule says git and remote actions happen only when the user asks. Offer a `claudeMdExcludes` entry for `~/.claude/settings.json` only when a line overrides session behaviour beyond git (for example "never ask, always proceed"); otherwise do not mention it.

## 3. Branch on state

**Worktree, main checkout has `CLAUDE.local.md`:** copy mode. Skip the questions. The content to write is the main checkout's file, byte for byte. If a local file already exists with the same hash, report "in sync" and stop. If the hashes differ, show a `diff` and offer to replace the local file with the main checkout's; on yes continue to step 5 with the main checkout's content.

**Main checkout, `CLAUDE.local.md` exists:** report it, run the drift check across every worktree in `git worktree list` (present and hash equal, present and differs, missing), and stop. The user runs the command inside any worktree that is missing or differs.

**No `CLAUDE.local.md` anywhere:** first run. Continue to step 4.

## 4. First-run questions (AskUserQuestion, one at a time)

1. **Notes tool.** "Tolaria (Recommended)" when the MCP is connected, else listed second; "No". Tolaria: the notes folder is `<vault root>/<Project>/`; if `list_vaults` returns more than one vault, ask which. No: ask for the notes folder path, one answer, no default inferred from the repo.
2. **Project name.** Default the repo directory name, kebab-cased. Used for the folder, the hub note and the `related_to` link.

Then look for a docs index in the notes folder: a file named `*index*.md`. Record its path or "none".

## 5. Announce, then wait

Print every path the run will create or modify, each with one line of purpose, grouped: work tree (`CLAUDE.local.md`, the exclude file), vault (folder, hub note, views, only when Tolaria and only those missing). Wait for the user's yes. Never create silently.

## 6. Apply

**One `patch` dispatch** with `Files: <top level>/CLAUDE.local.md, <exclude file>`, `Change:` the exact content below and "append the line `CLAUDE.local.md` to the exclude file if absent", `Check: git -C <top level> status --short --ignored CLAUDE.local.md` (expect `!! CLAUDE.local.md`). In copy mode the content is the main checkout's file.

Content for a first run, sections in this order, nothing else:

```markdown
@AGENTS.md

Personal planning, audits and reference notes for this project live in `<notes folder>`<Tolaria: (tolaria MCP `search_notes`; frontmatter `related_to: "[[<project>]]"`). `get_note` paths are relative to the vault root: `<Project>/<file>.md`.>

## Docs first

This codebase is mapped in the notes folder. Before reading code for any question, task or plan:

1. Read `<index path>` and pick the area doc(s) it points to.
2. Read those docs. They carry `file:line` footnotes; start from the files they name rather than searching.
3. Only then open code, and only the areas the docs point to.

Each doc's `verified_against` names the commit it was last checked against. When code and doc disagree, say so and treat the doc as possibly stale, not the code as wrong. Explore dispatches for this project name the relevant area doc(s) so the agent starts there.

## Session notes

A durable plan, audit or reference `.md` is saved to `<notes folder>`, never to `/tmp` or this repo<Tolaria: : frontmatter `type:` (`Plan`, `Audit`, else `Note`), `related_to: "[[<project>]]"`, `_width: wide`; kebab-case filename; first-line H1 title>.

A plan is one note per feature, updated in place, about one page: Goal, Done when, Decisions (each with why and what was rejected), Steps, Out of scope, Outcome. Only the next phase is specified in full; later phases get ten lines or fewer in the same note. No `-v2` files and no sibling notes for unbuilt phases. Name symbols and file paths, never line numbers or a "what exists" inventory; the area doc already carries current state. No session leftovers: ports, PIDs, scratchpad paths, sandbox workarounds, gate counts, pre-written commit messages. When the work commits, set `status` to Shipped and write Outcome (five lines or fewer: the commit hash and any deviation from the plan). When a later note changes a decision, edit the older note's decision in place and set `superseded_by: "[[<new note>]]"` on it. `status` is one of Draft, Active, Shipped, Superseded, Archived, nothing else. The daily-log entry for the work wikilinks its plan.

## Environment

Device, server and check rules for this repo go here (which simulator or browser, whose dev server, which viewport). Replace this paragraph or delete the section.
```

Rules for filling it: the `@AGENTS.md` line only when `AGENTS.md` exists at the top level and no root `CLAUDE.md` already imports it. The Docs first section only when an index was found; otherwise omit it and say so in the report. The angle-bracket Tolaria clauses appear only when Tolaria was chosen.

**Vault steps (main loop, Tolaria only, each skipped when present):** `<vault root>/<Project>/` and `<Project>/attachments/`; hub note `<vault root>/<project>.md` with `type: Project`, `status: Active`, `repo: <main checkout>`, `_width: wide`, H1 = project name, one-paragraph body; the four views `views/<project>-{audits,notes,references,work}.yml` cloned from an existing project's four views with the link swapped to `[[<project>]]`. If no project views exist to clone, skip them and say so.

## 7. Report

- Each path: created, replaced, skipped (already present), with the drift table for worktrees when one was run.
- The line: **No tracked file was changed.**
- The step-2 scan heading and its one sentence, repeated.
- Next: the worktrees still to run the command in, or "none".

## Re-running

Safe at any time. The main checkout run becomes the drift check; a worktree run becomes the copy. The main checkout's `CLAUDE.local.md` is the single source: edit it there, then run the command in each worktree.
