---
description: "Page through the uncommitted diff one file at a time as the user's own read, before anything is committed — read-only, main loop, ends with a paste-ready fix prompt, a commit split and a snapshot hash for the delta pass"
argument-hint: "[--delta <hash> | <plan path>]"
---

Subject: $ARGUMENTS

`/jun-walkthrough → orient on the plan → page the diff → close with three blocks, a split and a snapshot`

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
- Stop after every file and wait for "next".
- Every question or flag raised during the walk reappears in Phase 3. None
  may be dropped.

## Phase 1 — Orient

Find the plan yourself; the user does not type a path. Plans are named after
the worktree, so the slug is `basename $(git rev-parse --show-toplevel)` and
the last path segment of the branch (`feature/x` → `x`). Locate the project's
plan folder as the notes-routing skill describes — the docs-first pointer
(`CLAUDE.local.md`), the Tolaria vault via `search_notes`, committed repo docs
— and pick the plan whose filename or H1 contains the slug. State the pick in
one line. Zero matches: say the walk is unanchored and carry on. Several: list
them and ask. A plan path argument overrides all of this.

Read the part currently being implemented and its deviations section, so
"what changed" is judged against "what was asked". Note any deviation that
landed in the diff but was not recorded.

## Phase 2 — Page

Read `git diff` for uncommitted changes, plus untracked files from
`git status --porcelain --untracked-files=all`. Order: source first, then
hand-written templates and migrations, then tests.

Generated files — anything under `docs/` produced by a script, lockfiles,
snapshots — get one line naming them and are skipped. Nothing else is
skipped. If the user says "skip", note the file as unread for Phase 3.

Per file:

1. One sentence in plain English: what changed and why, before → after.
2. The hunks, in chunks of at most 150 lines, with a one-line gloss above
   each hunk saying what it does.
3. Flags, only if true: a missed reuse (name the existing thing,
   `path:line`); a refactor mixed with a behaviour change in the same file; a
   hardcoded value or bracket class that should be a token; a plan deviation
   not recorded.

Then stop. If the user asks for a change mid-walk, write it down for Block A
and page on; the fix happens in the build session after the last page.

## Phase 3 — Close

Three blocks, then two lines. Every walk question and flag lands in exactly
one block, and unread files are listed under Block A.

- **Block A — Fix prompt.** Paste-ready for the build session. One item per
  line: file, what is wrong, what done looks like. End with "Edit only these
  files: … No git."
- **Block B — Next-concern shape.** Anything structural: files, data flow,
  where state lives, what is out of scope.
- **Block C — Cleanup list.** Cosmetic items, to append to the plan's
  follow-ups.

Then the proposed commit split: one kind of change per commit, with the files
in each.

Then run `git stash create` and print its hash as `Snapshot: <hash>`, with the
instruction: after the fix lands, re-run `/jun-walkthrough --delta <hash>`. If
the tree is clean and the command prints nothing, say so instead.

The snapshot does not capture untracked files, so below it print one line per
file `git status --porcelain --untracked-files=all` lists as `??`:
`untracked <path> <blob>`, where `<blob>` comes from `git hash-object <path>`.
No `-w`; it writes nothing.

## Delta mode — `--delta <hash>`

`git diff <hash>` shows what changed in tracked files since the snapshot.
For untracked files, run `git hash-object` on every file
`git status --porcelain --untracked-files=all` lists as `??`, and page in
full only those whose blob differs from its recorded `untracked` line or that
have no recorded line. If the recorded lines are not in this conversation (a
new session ran `--delta`), say so and page every untracked file in full.

Page it the same way. Tick off each Block A item as answered or still open,
then re-propose the split. Print a new snapshot hash, with its `untracked`
lines, only if items remain open.
