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
