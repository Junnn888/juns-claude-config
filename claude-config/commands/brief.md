---
description: Shape rough notes into the labelled brief that starts a fresh session on a NEW bug or feature; with no notes it interviews you one question per turn; use /rebrief when decisions already exist
argument-hint: "[rough notes: symptom, trace, idea, constraints — or nothing, to be interviewed]"
---

Notes: $ARGUMENTS

Turn the notes into the brief that opens a fresh session. Print it inside one ```text fence and nothing else, so it can be copied whole. Pick the shape from the notes:

Bug — Symptom / Expected / Seen / Constraint / Prefer / Hunch / Setup
Feature — Goal / Done when / Constraint / Prefer / Setup

Interview: when the notes are empty, or they cannot fill Symptom or Goal, ask instead of guessing. One question per turn, in label order, and wait for the answer before asking the next. Each question is two short lines: what the label means in plain words, then an example answer. The first question picks the shape: "Bug (something behaves wrongly) or feature (something new)?". Then walk that shape's labels; the question for Hunch says it is a guess that the session will verify first. The user answers "skip" to leave a label out and "done" to stop early and print what is filled. Before printing, apply the decisions check below to the answers. Take facts from the answers in the user's words; never pad an answer beyond its one sentence.

Setup: optional last line, only when the next step needs it: how to reach the environment, as facts (accounts, fixtures, flags to set and revert, paths that overflow a tool). Never a port, a curl check, or an instruction to start, stop or restart a server: the session finds the server for its checkout by cwd, and asks the user when there is none.

One line per label, one sentence each, facts in the user's words. Rules:
- If the notes or answers name files, line numbers, locked decisions or an as-built state, print one line instead of a brief: "These notes carry decisions; use /rebrief."
- Symptom or Goal is required. If the notes cannot fill it, run the interview.
- Leave a label out rather than invent its line.
- Constraint is a boundary the solution must respect. Prefer is a tie-breaker between shapes that both work. Hunch is a guess about the cause, always written "Hunch (unverified): …, reproduce first".
- Name no file, no function and no cause outside the Hunch line; the session finds those.
- No history, no preamble, no sign-off.
