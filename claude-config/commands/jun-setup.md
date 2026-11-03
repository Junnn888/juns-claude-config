---
description: "Set up a repo for interactive sessions: survey its instruction files, ask Tolaria or not, write a git-excluded CLAUDE.local.md at the root (copied from the main checkout inside a worktree), point auto memory at the repo's one memory directory, optionally register the project in the vault. Nothing tracked is touched."
argument-hint: "[<repo path>]"
disable-model-invocation: true
---

Repo path argument: $ARGUMENTS
Top level: !`git rev-parse --show-toplevel 2>/dev/null || echo NONE`
Common git dir: !`git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo NONE`
Exclude file: !`git rev-parse --path-format=absolute --git-path info/exclude 2>/dev/null || echo NONE`

`/jun-setup → detect → scan repo instructions → worktree copy, or first-run questions → announce and wait → two patches write CLAUDE.local.md and the memory setting → report`

You orchestrate. The command installs nothing into the repository: the only files it writes inside the work tree are `CLAUDE.local.md` and `.claude/settings.local.json`, both git-excluded so they are never tracked. Every write inside the work tree goes through a `patch` dispatch; vault files are the main loop's own. You never run a git command that changes state, never install a dependency, never edit a tracked file.

## 0. Target

The repo is the argument above if given, else the top level shown. If it is `NONE`, stop: not a git work tree. The **main checkout** is the parent directory of the common git dir. This session is in a worktree when the top level differs from the main checkout.

The **memory target** is `~/.claude/projects/<slug>/memory`, where `<slug>` is the main checkout's absolute path with every character outside `A-Za-z0-9` replaced by `-`: `python3 -c 'import re,sys;print(re.sub(r"[^A-Za-z0-9]","-",sys.argv[1]))' "<main checkout>"`. Every checkout of the repo, main and worktrees alike, points `autoMemoryDirectory` at this one directory so preferences and conventions saved in one directory load in all of them. The value is written with a literal `~`, never expanded.

## 1. Detect

Read, do not write:

- Root instruction files: `CLAUDE.md`, `AGENTS.md`, `CLAUDE.local.md` at the top level; whether `CLAUDE.md` is only an `@AGENTS.md` import.
- The main checkout's `CLAUDE.local.md`, if any, and its hash; the hash of the local one, if any.
- Whether the exclude file already lists `CLAUDE.local.md`.
- `autoMemoryDirectory` in `<top level>/.claude/settings.local.json`: absent, equal to the memory target, or differs (compare with `~` expanded); and every other key the file holds, which the write must keep.
- Whether `git -C <top level> check-ignore -q .claude/settings.local.json` passes (exit 0: already ignored, no exclude line needed).
- Whether the tolaria MCP is connected (`list_vaults` answers).

## 2. Scan the repo's instructions (report only)

Grep `CLAUDE.md` and `AGENTS.md` for instructions written for automation: `branch`, `rebase`, `push`, `pull request`, `PR`, `commit`, `merge`, `worktree`, `own your`, `do not ask`, `without asking`, `proceed`. Print the matching lines with their line numbers under one heading, then one sentence: in this session those lines describe the project; the global rule says git and remote actions happen only when the user asks. Offer a `claudeMdExcludes` entry for `~/.claude/settings.json` only when a line overrides session behaviour beyond git (for example "never ask, always proceed"); otherwise do not mention it.

## 3. Branch on state

**Worktree, main checkout has `CLAUDE.local.md`:** copy mode. Skip the questions. The content to write is the main checkout's file, byte for byte. If a local file already exists with the same hash **and** the memory setting equals the target, report "in sync" and stop. A matching hash with the setting absent or differing continues to step 5 for the setting only. If the hashes differ, show a `diff` and offer to replace the local file with the main checkout's; on yes continue to step 5 with the main checkout's content.

**Main checkout, `CLAUDE.local.md` exists:** report it, run the drift check across every worktree in `git worktree list` with two columns per worktree: `CLAUDE.local.md` (present and hash equal, present and differs, missing) and memory setting (equal, differs, missing). If the main checkout's own setting is absent or differs, continue to step 5 for that setting; otherwise stop. The user runs the command inside any worktree that is missing or differs in either column. A worktree `git worktree list` marks prunable is reported as such; repairing is the user's call, not the command's.

**No `CLAUDE.local.md` anywhere:** first run. Continue to step 4; the memory setting is written alongside.

## 4. First-run questions (AskUserQuestion, one at a time)

1. **Notes tool.** "Tolaria (Recommended)" when the MCP is connected, else listed second; "No". Tolaria: the notes folder is `<vault root>/<Project>/`; if `list_vaults` returns more than one vault, ask which. No: ask for the notes folder path, one answer, no default inferred from the repo.
2. **Project name.** Default the repo directory name, kebab-cased. Used for the folder, the hub note and the `related_to` link.

Then look for a docs index in the notes folder: a file named `*index*.md`. Record its path or "none".

## 5. Announce, then wait

Print every path the run will create or modify, each with one line of purpose, grouped: work tree (`CLAUDE.local.md`, `.claude/settings.local.json`, the exclude file), vault (folder, hub note, views, only when Tolaria and only those missing). Then one line: `Memory: <memory target>`. Wait for the user's yes. Never create silently.

## 6. Apply

Two `patch` dispatches, the second skipped when the memory setting already equals the target, the first skipped when the setting is the only thing to write.

**Patch 1** with `Files: <top level>/CLAUDE.local.md, <exclude file>`, `Change:` the exact content below and "append the line `CLAUDE.local.md` to the exclude file if absent; also append `.claude/settings.local.json` if absent" (the second line only when the check-ignore test in step 1 failed), `Check: git -C <top level> status --short --ignored CLAUDE.local.md` (expect `!! CLAUDE.local.md`). In copy mode the content is the main checkout's file.

**Patch 2** with `Files: <top level>/.claude/settings.local.json`. `Change:` if the file exists, set the key `autoMemoryDirectory` to `<memory target>` and keep every other key and value byte for byte; otherwise create the file with `{"autoMemoryDirectory": "<memory target>"}`. `Check: python3 -c 'import json;d=json.load(open("<top level>/.claude/settings.local.json"));print(d["autoMemoryDirectory"], sorted(d))'`, expecting the target and every key found in step 1 still listed. If the write is refused, print the exact JSON and the path for the user to paste, and report the step as "left to the user".

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
- The memory line: `Memory: <memory target>` followed by created, replaced, in sync, or left to the user; then: "Run `/memory` in this checkout; the path shown must be <memory target>."
- The line: **No tracked file was changed.**
- The step-2 scan heading and its one sentence, repeated.
- Next: the worktrees still to run the command in, or "none".

## Re-running

Safe at any time. The main checkout run becomes the drift check; a worktree run becomes the copy. The main checkout's `CLAUDE.local.md` is the single source: edit it there, then run the command in each worktree. The memory setting is derived, never copied: every run recomputes the target from the main checkout's path and writes it only where it is absent or differs.
