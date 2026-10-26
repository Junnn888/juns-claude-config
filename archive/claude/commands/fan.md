---
description: Fan the task out to a multi-agent workflow with adversarial verification
argument-hint: "<task or question>"
---

Task: $ARGUMENTS

If no task was given above, take the most recent open request in this conversation; if
there is none, ask for one.

Typing /fan is my explicit opt-in to multi-agent orchestration — it satisfies the
Workflow tool's opt-in requirement. Don't ask for confirmation, and don't shrink the
structure to save tokens: by typing the command I've priced the task as worth a
workflow, and I control cost by choosing when to type it.

Orchestrate with the Workflow tool (parallel Agent calls in the same structure if it's
unavailable), sized honestly to the task — a small task earns a small workflow, an
audit earns dozens of agents. Adversarially verify substantive findings before they
reach me, label anything unverified, and note any coverage you deliberately bounded.
The final message follows my Output preferences: outcome first, findings ranked, one
concrete next action.

Tier model and effort per stage instead of running everything at one level — agent()
takes model and effort overrides, and I expect you to use them. Decide by what makes
each stage fail: effort buys breadth (exploration, tool calls), model tier buys
per-token judgment, so downgrade effort before you downgrade model, and downgrade
model only when the stage needs no judgment. Concretely: purely mechanical stages
(scans, greps, enumeration, reformatting) drop to haiku with no effort override (it
has no effort dial); volume reading/finding runs on sonnet at medium–high; quick
judgment stages (verify votes, dedup, triage) stay on the session model at low–medium
effort — a better model thinking less beats a cheaper one working harder; the final
judge/synthesis keeps the session model at high or above. Note each phase's model in
its meta entry so the tiering shows in the progress view.
