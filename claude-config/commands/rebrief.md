---
description: Write the five-line brief that carries this session's decisions into a fresh one, then /clear and paste it; use /brief for a new problem
argument-hint: "[the correct framing, if this session got it wrong]"
---

Correction from the user (may be empty): $ARGUMENTS

Commit plan first. Run `git status --short`. If the tree is dirty and the edits are work to keep (not exploration the user will revert), print a commit plan and stop; no brief yet. Never run `git add`, `git commit` or `git stash` yourself. Group the changes by concern, one commit each, in dependency order (shared code before its callers). Per commit: one sentence saying what it does and why, the files, then one pasteable line in a ```sh fence, in the project's commit style, no trailers: `git add path/a path/b && git commit -m "message"`. A file that mixes two concerns stays whole in the commit it mostly serves; name it and say which hunks the user could move with `git add -p` for a finer split. End with one line: "Paste each line in order, then say done for the brief." When the user says done, or runs this command again on a clean tree, re-run `git status --short` and `git log -1 --oneline` and continue below.

Write a brief for a fresh session that has none of this conversation. Print it inside one ```text fence and nothing else, so it can be copied whole. Five lines, each one sentence of at most 25 words, labelled exactly. Identifiers (paths, functions, selectors, variables, CSS tokens, data attributes, line numbers) appear only on the Files line; every other line is written at the altitude a user would describe the work.

Goal: what the work is for, in the user's words.
Done: the state the fresh session starts from: the commit hash, or the plan-note section that records the decision. Never diff size, file counts, test counts, selectors or measurements.
Next: the single next step as an outcome a user would notice, never the implementation (no "replace X with Y", no mechanism).
Files: at most three paths plus the plan note if one exists, no line numbers; the plan note carries the rest.
Framing: the one locked decision or assumption the next step depends on. If the correction above is non-empty, state it as a fact; never mention what was wrong before. A theory about a cause is not framing: write it as a sixth line, "Hunch (unverified): …, reproduce first".

Setup: optional last line, only when the next step needs it: facts the fresh session cannot get from CLAUDE.md, memory or the plan note (a fixture, a flag to set and revert, a non-default account). Omit anything those already carry (how to read the vault, dev-server rules, seeded passwords, tool names). Never a port, a curl check, or an instruction to start, stop or restart a server.

Rules: write the lines fresh from the conversation's current state, even if a brief or rebrief already exists in this session; never reuse, re-head or append to an earlier block. If nothing has been decided yet (no files, no as-built state, no locked decisions), print one line instead: "Nothing is decided yet; use /brief." Facts only, no history, no apology, no "previously". Name no file or decision the next step does not need. The fresh session starts from a clean tree at HEAD. Run `git status --short` and `git log -1 --oneline` before writing: either this session's work is committed and Done cites that hash, or it is exploration that the user will revert and Done cites only the plan record; never describe uncommitted edits or their diff size, and never hedge about which case holds. Before writing, update the project's plan note per its Session notes rule: decisions (with why and what was rejected), rules and done-when only, plus a 5-line Outcome when work is committed; findings, investigation and as-built detail stay out. The brief points at the note and does not restate it. Next begins from that committed or recorded state, as one step, and Setup never says to commit or stash.
