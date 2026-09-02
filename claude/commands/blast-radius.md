---
description: Map every surface this branch can affect, and name the consumers it did NOT update
---

Find the code that *should* have changed on this branch and didn't.

This runs before `/simplify` and before a CodeRabbit review. Those two review code that
exists. This one finds omissions — a consumer of a thing you changed, sitting in a file the
diff never touched, which no diff-scoped reviewer can see.

Argument (optional): $ARGUMENTS — a base ref to diff against. If absent, detect it.

Steps 1 and 2 run inline — they are cheap and you need the diff in your own context to
scope everything after. Steps 3 and 4 fan out to subagents, one per unit of work, spawned
in a single message so they run concurrently. Sweeping is a search that returns a short
list from a large amount of output, and classifying is a judgement that is more honest when
made by someone who didn't do the searching.

## 1. Establish the diff

Detect the base: use `origin/development` if it exists, else `origin/main`, else `main`.
State which you picked.

```
git diff --stat <base>...HEAD
git diff <base>...HEAD
```

Read the actual diff, not just the stat. You need the semantics of what changed, not the
filenames.

## 2. Extract the changed surface

From the diff, list every item in these four categories. Skip a category with one line if
the diff genuinely has none — don't invent entries to fill it.

**Exported symbols** — functions, types, constants, components added, renamed, or whose
signature or return shape changed.

**Data shape** — new or altered DB columns, new enum members, new fields on a shared type,
new values a status/kind field can now hold. Check migrations and `as const` maps.

**New variants of an existing entity** — the highest-yield category, and the one that
produces post-release bugs. Ask: does an existing row type now have a state it did not have
before? A flag, a subtype, a soft-delete marker, a shadow account. Every place that already
lists or counts that entity has silently inherited the new variant without being edited.

**Behavioural contracts** — a permission gate, an ordering guarantee, a filter, or a
default that other code relies on and this branch loosened or tightened.

## 3. Sweep for consumers — one `Explore` agent per item

Spawn one `Explore` agent per extracted item, all in a single message. Cap at 8; if there
are more items, group the related ones and give an agent the group. Give each agent:

- the one item it owns, described precisely enough to search for
- the list of files already in the diff, to exclude
- the instruction to search the whole repo, not the diff

Tell each agent to sweep exhaustively: LSP find-all-references for symbols; grep for
columns, string literals, and enum values. For a new entity variant it must search for
consumers of the **entity**, not the new flag — the blind spots are precisely the files
that never mention the flag, so searching the flag finds only the code that is already
handled.

Require each agent to return only a list of `file:line` candidates with a one-line note on
what that site does with the item. No analysis, no verdicts, no code excerpts — a sweeper
that starts arguing for its findings has already contaminated the next step.

Then subtract. Any consumer in a file the diff already touches is handled. **Everything
remaining is a candidate blind spot.** That subtraction is the whole point of the command.
Deduplicate across agents before going further — two items often lead to the same file.

## 4. Classify — fresh agents, one per candidate cluster

Group the deduplicated candidates by file or feature area and spawn one agent per group,
again in a single message. These must be new agents, not the sweepers: pass the candidate
`file:line` list and the change being assessed, but **not** the sweeper's reasoning about
why it looked promising. The point is an unanchored reader.

Instruct each classifier to read the file before judging, and to default to
`Deliberately unaffected` unless it can demonstrate otherwise. A missed blind spot costs
one bug; a fabricated one costs your trust in every future run of this command.

Every candidate gets a verdict. "Not sure" is not a verdict — go read the file.

| Verdict | Meaning |
|---|---|
| Needs update | Will behave wrong; describe the wrong behaviour |
| Deliberately unaffected | Correct as-is; state the reason it is immune |
| Needs a test | Correct today, but nothing pins it that way |

For every `Needs update`, the classifier must write the user-visible consequence as one
concrete sentence: who is looking at which screen, and what wrong thing do they see. A
finding without that sentence is not reportable — the agent either investigates further or
downgrades it. Require the sentence in the agent's returned output so you can enforce this
rather than write it yourself.

When the agents return, your job is synthesis, not re-investigation: dedupe overlapping
verdicts, rank by consequence rather than by how interesting the code is, and drop anything
whose consequence sentence describes behaviour the branch already handles. Spot-check any
`Needs update` that sounds severe before it reaches the report — a plausible blind spot that
turns out to be guarded upstream is worse than silence.

## 5. Report

Lead with the count of `Needs update` findings — or state plainly that there are none, which
is a legitimate and common result on a well-scoped branch.

Then, per finding: the file and line, the verdict, the one-sentence consequence, and the
suggested change. Group `Deliberately unaffected` into a single compact list — it exists to
show the sweep was exhaustive, not to be read line by line.

Do not apply fixes. Report only; the user decides what to act on and what to defer.

Close with a paste-ready block for the PR body:

```
## Blast radius
Base: <ref> · Consumers swept: <n> · Updated: <n> · Deliberately unaffected: <n>

Surfaces changed:
- <file> — <what a user sees differently>

Surfaces deliberately left alone:
- <file> — <why it is immune>
```

The second list is the load-bearing one. It converts an invisible omission into a recorded
decision, which is the only thing that makes the next reviewer able to challenge it.
