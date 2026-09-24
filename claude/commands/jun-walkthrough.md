---
description: "Page through the uncommitted diff one file at a time as the user's own read, before anything is committed — read-only, main loop, ends with a paste-ready fix prompt, a commit split and a snapshot hash for the delta pass"
argument-hint: "[delta [<hash>] | <plan path>]"
---

Subject: $ARGUMENTS

`/jun-walkthrough → orient on the plan → shape, then page the diff → close with three sections, one paste, a split and a snapshot`

You are paging the user through the uncommitted diff so they can read it
before it is committed. This is their review, not yours: you explain, they
decide. The diff they read must be the diff they commit.

## Rules

- Main loop only. Do not delegate pages to a `scout`; the whole point is one
  cheap read, and relaying a scout's page pays for it twice.
- Read-only. No edits, no fixes, no suggestions, no git writes.
  `git stash create` in Phase 3 is the one exception: it writes an object and
  touches nothing else — not the working tree, not the index, not the stash
  list.
- The code is the page. Every hunk is printed verbatim; a description of a
  hunk is not a page.
- Stop after every file and wait for "next".
- The walk raises no opinions on the code. Phase 3 carries only the user's
  questions and requests plus the mechanical tests-page notes, each under Fix
  now, Decide before next part or Later. None may be dropped.

## Phase 1 — Orient

Find the plan yourself; the user does not type a path. Plans are named after
the worktree, so the slug is `basename $(git rev-parse --show-toplevel)` and
the last path segment of the branch (`feature/x` → `x`). Locate the project's
plan folder as the notes-routing skill describes — the docs-first pointer
(`CLAUDE.local.md`), the Tolaria vault via `search_notes`, committed repo docs
— and pick the plan whose filename or H1 contains the slug. State the pick in
one line. Zero matches: say the walk is unanchored and carry on. Several: list
them and ask. A plan path argument overrides all of this.

Read the part currently being implemented and its deviations section, for
orientation on "what was asked". Deviations are the user's to raise while
paging.

## Phase 2 — Page

Read `git diff` for uncommitted changes, plus untracked files from
`git status --porcelain --untracked-files=all`. Order: source first, then
hand-written templates and migrations, then one page for all tests.

Generated files — anything under `docs/` produced by a script, lockfiles,
snapshots — get one line naming them and are skipped. Nothing else is
skipped. If the user says "skip" on a source, template or migration file,
note the file as unread for Phase 3.

Before page one, a shape page: one table, one row per changed file, tracked
and untracked. Columns: file, lines added, lines removed, new or existing,
exports added, callers per new export (a count from a grep of each new
export's name across the project). Below the table, one line listing new
dependencies from any manifest diff (`package.json`, `pyproject.toml`,
`go.mod`, etc.), or "none". Mechanical only: no judgment column, no
"important" marker. Count the pages from this table and head each one
"Page n of N". Then stop and wait for "next" before page one.

Per source, template or migration file:

1. One sentence in plain English: what changed and why, before → after.
2. Each hunk verbatim in a fenced `diff` block, at most 150 lines per block,
   with a one-line gloss above it. The user reads the code; the breakdown
   format's flow-altitude default does not apply here.
3. If the user skipped the file, one line: "file skipped by the user
   (unread)".

Tests are not paged as hunks. After the last source, template or migration
page, one page lists every changed test file with its test names (from
`it(`, `test(`, `describe(` or the language's equivalent), added names and
removed names marked. Notes on that page, only if true: a deleted test; a
test file with no source counterpart in the diff; a source file in the diff
with no test change.

Then stop. If the user asks for a change mid-walk, write it down for Fix now
and page on; the fix happens in the build session after the last page.

## Phase 3 — Close

Three sections, then one paste, then two lines. Every user question and
request, and every tests-page note, lands in exactly one section, and unread
source files are listed under Fix now.

- **Fix now.** Pasted to the build session.
- **Decide before next part.** Anything structural — files, data flow, where
  state lives, what is out of scope. Recorded in the plan's next part as open
  decisions, never sent to a builder now.
- **Later.** Cosmetic items. Appended to the plan's follow-ups.

Then ONE paste-ready prompt for the build session. It opens with this
preamble, verbatim:

> Before implementing anything, verify that each item below is a real issue.
> Treat every item as a claim, not a confirmed defect: read the code it names,
> confirm the problem holds, and skip any that do not, saying which and why.
> Only then apply the fix.

Then:

1. The Fix now items, one per line: file, what is wrong, what done looks
   like.
2. "Record the Decide before next part items in the plan's next part as open
   decisions", with those items.
3. "Append the Later items to the plan's follow-ups", with those items.
4. End with "Edit only these files: … No git."

Then the proposed commit split: one kind of change per commit, with the files
in each.

Then run `git stash create` and print its hash as `Snapshot: <hash>`, with the
instruction: after the fix lands, re-run `/jun-walkthrough delta`. The hash is
still printed for a delta run in a new session. If the tree is clean and the
command prints nothing, say so instead.

The snapshot does not capture untracked files, so below it print one line per
file `git status --porcelain --untracked-files=all` lists as `??`:
`untracked <path> <blob>`, where `<blob>` comes from `git hash-object <path>`.
No `-w`; it writes nothing.

## Delta mode — `delta [<hash>]`

`delta` with no hash uses the most recent `Snapshot:` line printed in this
conversation, with its `untracked` lines. If no `Snapshot:` line is in this
conversation, ask for the hash rather than guessing. `delta <hash>`
overrides, for a delta run in a new session. The `--delta` spelling is still
accepted.

`git diff <hash>` shows what changed in tracked files since the snapshot.
For untracked files, run `git hash-object` on every file
`git status --porcelain --untracked-files=all` lists as `??`, and page in
full only those whose blob differs from its recorded `untracked` line or that
have no recorded line. If the recorded lines are not in this conversation (a
new session ran `delta <hash>`), say so and page every untracked file in
full.

Page it the same way. Tick off each Fix now item as answered or still open,
then re-propose the split. Print a new snapshot hash, with its `untracked`
lines, only if items remain open.
