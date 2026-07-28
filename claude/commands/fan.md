---
description: Fan the task out to an unrestricted multi-agent workflow with adversarial verification
argument-hint: "<task or question>"
---

# /fan — multi-agent fan-out

Task: $ARGUMENTS

If no task was given above, take the most recent open request in this conversation; if
there is none, ask for one.

Typing this command is the user's explicit opt-in to multi-agent orchestration — it
satisfies the Workflow tool's opt-in requirement. Do not ask for confirmation before
spawning agents, and do not economise the structure to save tokens: scale is the point
of the command, and the user controls cost by choosing when to type it.

## Rules of engagement

1. **Orchestrate with the Workflow tool** — deterministic control flow (`pipeline`,
   `parallel`, loops), not a chain of ad-hoc sequential agents. If the Workflow tool is
   unavailable in this harness, fan out with parallel Agent calls in the same structure.
2. **Scout inline first, briefly.** Identify the work-list — files, subsystems,
   questions, dimensions — so the fan-out is grounded. Discovery of the list only; the
   work itself belongs to the agents.
3. **Decompose wide, not deep.** Prefer more, narrower agents over fewer broad ones:
   one agent per independent unit (file cluster, review dimension, hypothesis, search
   modality). There is no agent-count ceiling; match the count to the task honestly — a
   small task earns a small workflow, an audit earns dozens.
4. **Adversarially verify every substantive finding** before it reaches the user:
   independent verifiers prompted to REFUTE the claim, majority vote (three votes for
   load-bearing claims, with diverse lenses — correctness, reproduction, security or
   performance where relevant). Anything unverified is labelled as such, never silently
   included.
5. **Synthesise, then completeness-check.** A synthesis stage that leads with the
   outcome, then a critic agent asking "what's missing — an angle not run, a claim
   unverified, a consumer not checked?" Real gaps trigger one more round; stop after
   two consecutive rounds that surface nothing new.

## Shapes to reach for

- **Discovery** (bugs, edge cases, unknowns): loop-until-dry — keep spawning finders
  until two consecutive rounds return nothing new.
- **Review**: dimensions → find → adversarial verify, pipelined per dimension so fast
  dimensions never wait on slow ones.
- **Research**: multi-modal sweep (different search angles, blind to each other) →
  deep-read → synthesis.
- **Design**: N independent attempts from different premises → judge panel →
  synthesis from the winner, grafting the best of the runners-up.
- **Migration / broad sweep**: discover sites → transform per site (worktree isolation
  if parallel edits would collide) → verify per site.

## Reporting

- `log()` any coverage you bound (top-N, sampling, skipped angles) — no silent
  truncation.
- The final message follows the user's Output rules: verdict first, findings ranked,
  verified/unverified labelled, one concrete next action.
