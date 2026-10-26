---
description: "Explain a topic, the previous answer, or a branch's changes at flow level — where data comes from, how it is fetched, compared, stored and shown — with no code identifiers unless asked"
argument-hint: "[<topic> | <base ref>]"
---

Subject: $ARGUMENTS

`/flow → resolve the subject → explain the mechanism as stages → diagram if it branches`

You are explaining how something works to someone who owns the system but does
not read its code. They need the flow: where data comes from, how it is
fetched, how it is transformed or compared, where it is stored, what the user
sees. They do not need file names, function names, or types unless they ask.

## Resolve the subject

- No argument: re-explain your previous answer in this conversation at flow
  level. Do not re-investigate; the facts are already in context.
- A git ref (a branch name, `origin/…`, a SHA, or anything `git rev-parse`
  accepts): explain what the branch changes. Dispatch one `scout` for
  `git diff <ref>...HEAD` plus working-tree changes and ask it for the data
  flow before and after, not a file list. Then explain the change as
  before → after.
- Anything else is a topic or question. Answer from context if you can;
  otherwise one `scout` dispatch for the mechanism, asking for the flow, not
  `path:line`.

## Shape

1. One sentence: what the whole thing does, in plain English.
2. Numbered stages, one or two sentences each, only the stages that apply:
   source (where the data originates), fetch (how it is retrieved, and by
   whom), transform or compare (what is computed, matched, or decided), store
   (where the result lives and for how long), surface (what the user sees and
   when). For a branch, state each stage as before → after and skip stages the
   branch does not touch.
3. A compact ASCII diagram (`A → B → C`, one line per branch) when the flow
   branches; skip it for a straight line.
4. Optional last block, "Where to look": at most five paths, one line each,
   for when they want to open the code. No other identifiers anywhere in the
   answer.

Keep the prose to about 150 words. No code blocks other than the diagram. If
the honest answer is that a stage is not knowable from the codebase (an
external service's behaviour, for example), say which stage is a black box and
what is known about its inputs and outputs.
