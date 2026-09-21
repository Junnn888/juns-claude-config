# global-claude-md-spec

Source of truth for the design decisions behind **juns-claude-config** and their rationale.
The config is built in layers; each component earns its place only under the governing
principle below. (Note: the working files currently live under `claude/` in this repo, even
though the README narrates an intended flat layout.)

## Governing principle

A new component — a `CLAUDE.md` rule, a hook, a skill, or a plugin — is built **only** if it
catches a failure nothing else deterministically catches, **or** a workflow is repeated 3+ times
with gotchas worth freezing. No speculative features; nothing added "while we're here."

## Layers

| Layer | Status | What |
|-------|--------|------|
| 1 — CLAUDE.md | Built | Global behaviour rules and output preferences: surface-uncertainty, scope/completeness, output shape, edit-surface, execution discipline, safety, British-English. Provenance-traced from Karpathy / gstack / Anthropic guidance. |
| 2 — Hooks | Built | `permissions.deny` list + matcher-scoped hooks: two PreToolUse safety **command** hooks (`safety-bash.sh`, `safety-files.sh`). |
| 3 — Skills | Built | 1 skill (`notes-routing`). Two qualifying triggers: a workflow repeated 3+ times with gotchas / checkpoints / isolation, **or** situational reference material that would otherwise sit always-on in CLAUDE.md (added 2026-07-27, below). |
| 4 — LSP | Built | Official first-party LSP plugins (`claude-plugins-official`), 12 languages. Installing one auto-enables Claude Code's built-in LSP tool. Binaries are check-and-report only (never auto-installed — irreducible supply-chain surface). |
| 5 — Orchestration | Built | `Orchestrator` output style (default via `outputStyle`; switch with `/config`) + agent roster (`scout`/`patch`/`builder`/`deep`) pinning model+effort tiers for delegation. Steady-state delegation only; scale fan-outs stay behind `/fan`. |

### Layer 1 — CLAUDE.md
Behaviour rules only; kept short so it loads cheaply every session. Each rule must change
behaviour the model wouldn't reliably reach on its own.

### Layer 2 — Hooks
Matcher-scoped, never global-fire; target <200ms for command hooks; exit 2 for hard enforcement.
The deny-list is belt-and-braces only — Bash deny patterns are fragile and don't cover
subprocesses, so the **hooks** are the real enforcement.

- `safety-bash.sh` — PreToolUse(Bash). Hard-blocks dangerous command categories (git state,
  DB/migrations, destructive FS, deploy, secrets, dep-adds, mutating HTTP, system, CI).
- `safety-files.sh` — PreToolUse(Read|Write|Edit|MultiEdit). Blocks reads and edits of `.env*`, keys, credentials.

### Layer 4 — LSP
See README "LSP layer". Official plugins over self-authored/third-party (supply chain); binaries
reported, never auto-installed.

---

## Layer 2 addendum — Plan-reviewer rubric & hook (2026-06-04)

**Need.** A plan that writes or changes code can silently skip a quality axis ("looks fine,
ship it"), and nothing catches it — the failure is the *absence* of an assessment, which the
planning model is exactly the wrong party to police on itself.

**Hook** — `claude/settings.json` → `PreToolUse` / matcher `ExitPlanMode`, `type: "prompt"`,
`model: "claude-sonnet-5"`. A single-turn model evaluation that fires at plan-exit and checks only that
each of the six axes (simplicity, over-engineering, logic/correctness, UX, performance,
verification plan) carries a specific, falsifiable note — not whether the plan is *good*
(it cannot verify performance or correctness against the real codebase). Approves if all six
are addressed; otherwise denies and lists the missing/hand-waved axes.

**Rubric removed from CLAUDE.md (2026-07-27).** The matching *Coding-plan assessment* rule was
dropped from `claude/CLAUDE.md`. It duplicated the hook while costing context every session, and
it collided with three `## Output` rules — six axes breached the 5-item list cap, six concern
notes breached the one-caveat cap, and an assessment placed before the plan breached lead-with-
the-answer. The hook is now the only carrier: it fires only at plan-exit, and its deny reason
names the missing axes, so the model learns the rubric exactly when it needs it.

**Decisions.**
- **Gate, not advisory.** A deny blocks `ExitPlanMode`; the reason is fed back so the model
  revises and retries. (Advisory alternative — always-allow + `additionalContext` — was rejected:
  the value here is the stop, not a note.)
- **Model `sonnet`, not the fast default.** The fast default rubber-stamps; Sonnet is capable
  enough for a five-axis presence check without the cost/latency of Opus on every plan-exit. Alias
  form so it tracks the current Sonnet rather than rotting to a pinned id.
- **Verbatim gate for non-code plans.** No exemption clause was added. `ExitPlanMode` is documented
  as code-implementation-only, so non-code plans through it are an accepted edge case.

**Output contract (verified verbatim against `code.claude.com/docs/en/hooks`).** A `type:"prompt"`
PreToolUse hook returns its decision via `hookSpecificOutput`:

```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
  "permissionDecision": "deny", "permissionDecisionReason": "<reason>" } }
```

`permissionDecision` ∈ `allow | deny | ask | defer`. The harness elicits this structured decision
from the model, so the prompt states criteria + when to approve/deny — no JSON-output instructions
in the prompt text. (A `{"ok": true/false}` shape is **not** the current contract.)

**Governing-principle justification.** Passes: it catches a failure nothing else deterministically
catches — a plan reaching execution with an unassessed axis. The rubric alone relies on the model
not skipping it; the hook makes the check deterministic at the one moment (plan-exit) where it can
still change the outcome, using an independent model the planner can't talk past.

**Cost.** Matcher-scoped to `ExitPlanMode` → zero overhead on normal turns, Bash, or edits. One
Sonnet single-turn eval per plan-exit.

**Post-migration watch (2026-07-27).** The gate is unvalidated against the current planner
generation (the judge model, Sonnet 5, did not change in the migration — only the planner did).
The check it performs is presence-of-assessment, which is planner-independent, so no harness is
being built pre-emptively. Watch condition: if the gate denies a plan twice in a row on the same
axes, or starts denying plans that visibly address all six, record the transcript and revisit —
that is the deny-loop failure the 2026-07-08 reconciliation existed to prevent.

---

## Layer 2 addendum — status line & settings sync (2026-06-25)

**Status line.** `claude/statusLine.sh` renders `model · <n>k tok (<pct>%)` from the harness's
status JSON via `jq`; wired through `settings.json` → `statusLine` (command type, `~/.claude/
statusLine.sh`). `install.sh` copies it to `~/.claude/` and `chmod +x`; `jq` is already a documented
prerequisite, and the script prints nothing without it (graceful degrade, no error).

**Settings folded in from live config.** `effortLevel: high`, `tui: fullscreen`,
and an `enabledPlugins` block (12 LSP + `frontend-design` + `code-simplifier`). Deliberately **not**
shipped: `coderabbit` (left to per-user opt-in), `skipWorkflowUsageWarning`, `agentPushNotifEnabled`
(personal UX prefs). The two non-LSP plugins are pre-installed by `install.sh` alongside the LSP loop.

---

## Layer 1+2 addendum — six-axis plan gate & hardened git rule (2026-07-08)

Applied from the 2026-07-08 config audit (audit, playbook, and eval kit kept
privately outside this repo, in `~/claude-fable-kit/`).

**Plan gate reconciled and extended.** The CLAUDE.md rubric ("stay silent on fine
axes") contradicted the ExitPlanMode hook ("silence fails") — a deterministic
deny-loop, acute on literal models. Resolution: a note is now a concrete concern
*or* a specific reason the axis is a non-issue; silence fails. A sixth axis —
**verification plan** (the commands/tests that will demonstrate correctness, named
before implementing) — was added to both rubric and hook prompt: unprompted
verification is the largest Fable-vs-fallback gap (PLAYBOOK.md §1), and plan-exit
is the one deterministic moment to demand it.

**`safety-bash.sh` rule 1 hardened.** Named bypass: `git -C <path> commit` /
`git -c k=v commit` (subcommand not adjacent to `git`); named false positives:
quoted/argument-position matches (`echo git commit …`, `printf 'note: git push …'`).
Fix: strip quoted segments, anchor to command position (start or after `;&|(`,
allowing `VAR=val` prefixes), tolerate dash-flags with an optional value argument
before the subcommand. Verified against a 13-case block/allow harness (in the
private eval kit, `04-hook-hardening`) plus 12 sanity cases across the other rule
categories. Those other rules
still match the raw lowercased string — migrating each to the stripped form needs
its own harness cases per category, deliberately not done as a drive-by.
(2026-07-09: rule 9 — `gh`/CI — was migrated after a live false positive: with no
anchor, "hi**gh run**" inside quoted text matched `gh run`. Same fix shape, 9-case
harness + 13/13 regression. Rules 2-8 remain on the raw string, pending the same
treatment.) Known
residual (documented, accepted): `bash -c "…"`, `xargs`, `eval` remain regex-unclosable.

---

## Resolved — response shape (2026-06-05 deferred, 2026-07-27 reframed and fixed)

**Original symptom (2026-06-05).** Responses ran verbose — code snippets that don't change the next
action, plus sentence padding — despite the Layer 1 Output concision rules already in `CLAUDE.md`.
Deferred at the time to protect the plan-reviewer change's scope and keep its test uncontaminated.

**The deferral reasoning was wrong on two counts, corrected 2026-07-27.**

*First, it was never mode- or model-specific.* The original note scoped the symptom to
ultracode/high-effort on a particular model and concluded "the symptom is mode-specific; the fix
must be too". It recurred on the next model generation in ordinary sessions with no exhaustive-mode
directive in play. Treat response shape as a standing property of the config, not a property of a
model or a mode — model names are deliberately absent from this section, and belong in it only if a
future failure is genuinely traced to one.

*Second, the target metric was wrong.* The note (and the rules it was defending) optimised for
**token count**. The actual cost is **interpretive load** — a 5-sentence paragraph that must be read
linearly and unpacked is worse than a longer numbered list, despite being fewer tokens. These
diverge: "step 3 of 5" is ~4 tokens and zero parsing cost.

**Why the old rules failed.** All six were *subtractive* — "cut", "don't narrate", "at most one",
"shortest response that fully answers". Every one constrained length; none constrained form. So they
were satisfiable by writing a shorter dense paragraph: compliant, still unreadable. They were also
self-judged ("fully answers", "anything that doesn't change the answer"), the same unfalsifiability
the plan-reviewer hook exists to catch in plans.

**Fix shipped (2026-07-27).** `## Output` rewritten as ten *form* rules with an explicit preamble
stating the axis, so the section can't be re-read as "be brief". Countable where possible: paragraphs
cap at 3 sentences, lists cap at 5 items. Structural where not: prose is for one idea, more than one
takes a numbered list / bullets / table. Plus restate-step-position each turn, end on one concrete
next action or stop, matter-of-fact error tone, and estimates only for user-run actions. A
scale-to-size rule keeps one-line answers at one line.

**Extended to fourteen rules, same day, after the eval.** A second pass over
`ayghri/i-have-adhd` (see *Provenance*) added four rules the original ten had no equivalent for, and
the preamble gained a persistence clause. The section now carries **fourteen** rules; the four
additions post-date the measurement below and are therefore unmeasured.

**Provenance.** Rules 2, 3, 5, 8, 9, 10 adapted from `ayghri/i-have-adhd` (MIT), whose ruleset
targets actionability for an ADHD reader. Adopted as form rules, not concision rules — that project
weights concision at only 10% of its own rubric, and three of its rules add lines while removing
interpretive load. Its always-on delivery (opt-in flag file + `SessionStart` hook injecting the
ruleset) was deliberately **not** adopted: it duplicates what `CLAUDE.md` already does here, and the
flag file exists to make the behaviour default-off for a public plugin's users — optionality this
config doesn't want.

**Second pass over the same source (2026-07-27).** A behavioural diff of the two rulesets — not a
text diff — surfaced four things that source produces and the ten rules had no rule for. All four
add lines and remove parsing work, which is the test this section is judged on:

- **Options format.** "What are my options" gets two to four ranked options, recommendation first,
  one line of trade-off each. Previously unruled, so option-shaped prompts fell back to defaults.
- **Completed-work visibility.** State what now works and how to see it. This required narrowing the
  old blanket recap ban, which was suppressing the useful line along with "I've now done X, Y and Z".
- **Pre-send deletion pass.** Cut announcing openers, "anything else?" closers, "by the way"
  sidebars, empty hedges, and idioms — the last two had no rule at all. Keeps hedges carrying real
  uncertainty, since deleting those manufactures confidence.
- **First-line/last-line check.** An acceptance test rather than a prohibition: read only those two
  lines and you should know what to do next and what just happened.

The preamble also gained a persistence clause (rules do not lapse on topic change or session
length). Still not adopted: that project's time-estimate rule, which would have the agent estimate
its *own* work — this config's rule 11 forbids exactly that.

**Governing-principle status.** Cleared as a Layer 1 rule change, not a new component. No hook was
built: the earlier sketches (an effort-scoped nudge, a narrow `Stop` hook) both assumed the
token-count framing, and a second injection point was never the constraint — unfalsifiable rules
were.

**Measured (2026-07-27).** Harness built in the private kit at `~/claude-fable-kit/shape-eval/`
(cases, rubric, runner, blind judge; archived scores under `results/`). Eight prompts against a copy
of this repo, each arm a different `## Output` section in an isolated `CLAUDE_CONFIG_DIR`, judged
blind on scannability / correctness / actionability / safety / concision.

Definitive run — 3 arms x 8 cases x 2 trials, 48 responses, Opus 5 @ 1M, effort `high`:

| Arm | Scannability | Correctness | Actionability | Weighted |
|-----|--------------|-------------|---------------|----------|
| 10 rules | 4.94 | 4.56 | 4.75 | 4.77 |
| 6 rules (trimmed)  | 4.56 | 4.38 | 4.56 | 4.52 |
| 0 rules (control)  | 4.44 | 4.31 | 4.38 | 4.42 |

The winning arm is the **ten-rule** section, which is not what currently ships — four more rules
were added the same day, after this run. Read the table as evidence that form rules beat no rules
and that trimming hurts, not as a score for the shipped fourteen.

Monotonic in all five dimensions; no blockers in any arm. Mechanically, the 10-rule arm also had the
lowest prose share (41% vs 45% for no rules), twice as many tables, and the shortest responses.

**Three findings worth keeping.**

*The section earns its place.* Against no `## Output` at all, the rules raise scannability 4.44 -> 4.94
while correctness *rises* rather than falling. The formatting-vs-task-accuracy interference reported
in the literature does not appear at this ruleset size on these cases.

*The countable caps are load-bearing.* The trimmed arm dropped the 5-item list cap and immediately
produced a 7-item list; both capped arms never exceeded 5. The caps looked redundant in an earlier
single-trial run because that run never provoked them.

*Two "concision" rules were added and reverted.* "Cut by selection, not compression" and a
no-re-explaining rule failed their own gate — correctness 4.71 -> 4.43 and prose share moved the
wrong way (40% -> 45%). They compressed rather than selected, which is what the wording was meant to
prevent. Reverted the same day.

**Methodological note, recorded because it nearly caused a wrong decision.** A 3-arm run at one trial
(n=8/arm) showed the arms within a few points and prompted a recommendation to *delete* most of the
section. Doubling to two trials (n=16/arm) separated them cleanly and reversed the conclusion. Effects
at this scale are below the noise floor of a single trial — do not act on one.

**Known bias.** The judge ran under the live config (the isolated judge dir cannot reach the keychain
without a long-lived token), so it was primed toward the shipped ruleset. That inflates the 10-rule
arm specifically; it does not affect the mechanical metrics, which point the same way. Treat the gap
as directionally right and smaller than measured.

---

## Commands addendum — /fan (2026-07-28)

**Need.** Fable-class models fan work out to subagents naturally; Opus-class models
under-delegate unless prompted with per-message magic words ("ultracode", "fan out",
"adversarially verify"), which the user was typing repeatedly. A CLAUDE.md rule would be
probabilistic (prose compliance) and always-on; a command is deterministic on invocation
and free otherwise.

**Decision.** `claude/commands/fan.md` — `/fan <task>` loads a prescriptive fan-out recipe:
brief inline scout → Workflow-tool orchestration, wide decomposition with no agent-count
ceiling, adversarial majority-vote verification of substantive findings, synthesis plus a
completeness critic with a two-dry-rounds stop. The ambition is encoded in the command body
precisely so a conservative model cannot shrink the structure; invocation itself satisfies
the Workflow tool's explicit-opt-in requirement. Cost control is the opt-in: typing the
command is the user pricing the task as worth a workflow. Pairs with the user-side
"workflow size: unrestricted" setting.

**Governing-principle justification.** Passes: deterministic delivery of a behaviour the
model won't reliably reach on its own, and a correction the user was already repeating 3+
times by hand.

## Layer 2 addendum — Stop quality gate and subagent hand-back truth (2026-09-18)

**Need.** Agent-driven work was arriving as thousand-line, over-complicated diffs, and the
rules meant to hold it back are advisory: CLAUDE.md is injected as user-turn context in a
"may or may not be relevant" system-reminder, and compliance decays as generation runs on
— arXiv 2605.10039 measures roughly 5.6% lower odds of instruction compliance per
additional function generated. Anthropic's own hook documentation draws the line: hooks
execute deterministically, context files only ask. Two failures were surviving every
advisory rule. First, a turn could end with lint or typecheck red, because "run
tests/typecheck/lint where applicable" is a request the model can quietly skip. Second, a
subagent's report is self-narrated: its file list and its `Reused:` / `Wrote new:` line are
claims from memory, and the orchestrator could only check them by re-reading the tree.

**Decision.** Two hooks.

`claude/hooks/quality-gate.sh` (Stop) reads the hook payload, and in any git repo whose
`package.json` declares `scripts.lint` or `scripts.typecheck` runs them through the
lockfile's package manager, blocking the stop with exit 2 and the last 40 lines of the
failing output plus an explicit "fix the root cause, do not disable rules or add
suppressions" instruction. It deliberately does *not* early-exit on `stop_hook_active`:
the gate must re-check after each fix attempt, and Claude Code's override after 8
consecutive blocks is the runaway guard. Cost is contained by a per-session tree
fingerprint — sha1 of `git diff HEAD` plus the untracked file list with sizes and mtimes,
stored per session and updated only on a pass — so a turn that changed nothing since the
last green run, or a clean tree, skips the checks entirely.

`claude/hooks/handback-truth.mjs` (SubagentStart + SubagentStop, matcher
`^(builder|patch)$`) snapshots tracked `--numstat` deltas and untracked line counts when a
writer agent starts, recomputes them at stop, and blocks once with a facts block listing
changed files, created files and new exported symbols. A SubagentStop block is delivered to
the *subagent*, not the parent, so the block cannot inject anything into the orchestrator's
context directly; instead it instructs the agent to reconcile its own report with the facts
and append them verbatim, which reaches the orchestrator inside the hand-back it already
reads. `stop_hook_active` releases the agent on the second stop, and an agent that changed
nothing never bounces at all.

**Governing-principle justification.** Passes on both counts. Lint or typecheck red at the
end of a turn is caught by nothing else deterministically — the model's own promise to run
them is the thing that decays. And a subagent report's file and reuse claims have no other
mechanical check: no reviewer, hook or style compares what the agent says it did against
what the tree records.

**Exception to the <200ms target.** The repo's hook budget assumes PreToolUse hooks that
fire on every tool call. `quality-gate.sh` fires once per turn on Stop, and only pays for
lint and typecheck when the tree changed since the last pass, so a Q&A turn costs a git
diff and a hash. Its `timeout` is set to 300s in `claude/settings.json` — well under the
600s command-hook default, and enough for a cold `tsc` on a large project.

**Rules out.** SubagentStop writing into the parent's context: undocumented, and the
documented behaviour routes the block to the subagent. PostToolUse on the Agent tool as an
alternative trigger: it fires at launch for background agents, so it cannot observe the
finished work. Early-exiting `quality-gate.sh` on `stop_hook_active`: that turns the gate
into a bounce-once nag, which is the opposite of a gate — one ignored failure and the turn
ends red.

## Layer 5 — Orchestrator output style & agent roster (2026-08-03)

**Need.** On expensive main-loop models the user was re-typing the same delegation
preamble ("act as an orchestrator, dispatch opus/sonnet agents at varying effort, do the
work yourself only when it's genuinely hard") session after session. Two gaps, two
mechanisms:

1. *Session-wide role* — a `UserPromptSubmit` hook was considered and rejected: it re-pays
   the injection every turn, can't reach the system prompt, and catches nothing an output
   style doesn't already catch deterministically. Output styles are the purpose-built
   mechanism: appended to the system prompt once (cached), with built-in adherence
   reminders, toggled per-session via `/config`, and scoped to the main conversation only
   (subagents don't inherit them, so the role can't recursively infect workers).
2. *Effort tiering* — the Agent tool's inputs are `description`/`prompt`/`subagent_type`/
   `model`/`isolation`: **no effort parameter**. Per-dispatch effort exists only in
   Workflow's `agent()` opts (already /fan's domain) and in agent-definition `effort:`
   frontmatter. So a roster of definition files is the only way ordinary delegation can
   vary effort — and the built-ins can't substitute, because they `model: inherit` (on a
   Fable session, `general-purpose` runs Fable, defeating the purpose).

**Decision.** `claude/output-styles/orchestrator.md` (`keep-coding-instructions: true` —
the role changes *who does the work*, not the engineering rules) + three agents pinning
model×effort by what makes each stage fail: `scout` (sonnet/medium, read-only tools —
breadth needs tool calls more than thinking), `builder` (opus/high — implementation kept
a tier below the fable main loop, effort pinned so it doesn't track the session), `deep`
(opus/xhigh — the one place per-token judgment is the point; promote to fable only on
demonstrated misses). Tiers revised same day from sonnet/low and sonnet/high on the user's
call. Custom names rather than overriding the
built-in `Explore`, so behaviour changes only when the style is selected. The style tells
the model to suggest `/fan` for genuine fan-outs rather than improvise one — Workflow
opt-in and cost control stay with the user. Not enabled by default at first: `outputStyle` was left
out of `settings.json`; selection was per-user via `/config` (superseded 2026-09-08, below).

**Revision — default on (2026-09-08).** `"outputStyle": "Orchestrator"` now ships in
`claude/settings.json`, so a fresh install starts every session in the strict-manager
role. Rationale: every session since 2026-08-04 ran under the style anyway, so per-user
opt-in had become a step re-done on each machine for no decision it still protected.
Cost control is unchanged — the style delegates to the roster, and scale fan-outs still
wait on `/fan`. Opting out is `/config` → Output style → Default, per user.

**Governing-principle justification.** Passes: deterministic delivery of a behaviour the
model won't reliably hold across a session (delegation discipline decays), replacing a
preamble the user was already re-typing 3+ times; the effort-tier roster catches a gap
(per-agent effort) nothing else in the config can express.

**Revision — strict manager (2026-08-04).** The original style kept a "do the work
yourself when" escape hatch (context too expensive to hand over, dispatch prompt dearer
than the edit, genuinely hard). In practice Fable used it to self-execute whenever it
judged itself best placed — correct on quality, wrong on the whole point of the layer,
which is protecting main-loop usage. The hatch is removed: Fable never edits, writes, or
implements; a hard task means a Fable-authored plan handed to `deep`/`builder` in full
(files, constraints, restated context, acceptance criteria), and a failed dispatch means
sharper instructions or a tier escalation, never a takeover. Direct reads and read-only
commands stay allowed where routing or verification demands them — the manager still has
to judge the work — and answering from held context needs no agent.

**Revision — `patch` agent (2026-08-04).** Removing the escape hatch made every trivial
one-liner cost an opus `builder` dispatch. The user's call: add a fourth roster agent,
`patch` (sonnet/medium), for small fully-specified fixes where the whole change fits in
the dispatch prompt. Model tier follows the roster's own rule — the orchestrator has
already done the thinking, so the fix needs no per-token judgment. Effort was initially
low, raised to medium the same day on the user's call: medium is the roster-wide effort
floor. The agent self-polices scope: if it finds itself
exploring or designing, it stops and reports the task as builder-sized rather than
guessing.

**Revision — scout on 1M context (2026-08-04).** `scout`'s frontmatter pins `model:
sonnet[1m]` — the suffix is accepted there (verified by a live dispatch) and gives
repo-wide sweeps the full 1M window. `patch` stays on plain sonnet (200k) on the user's
call: a fix that can't fit a 200k window isn't a patch — it escalates to an opus agent.
The 1M variant bills at premium rates only for requests exceeding 200k, so the scout pin
is free until a sweep actually needs the headroom.

**Revision — effort trims from transcript evidence (2026-08-13).** First measurement of
the layer in production: 50 orchestrated sessions, 310 roster dispatches analysed from
`~/.claude/projects/*/</session>/subagents/` transcripts. Findings: the suspected
feedback-loop cost doesn't exist (6/310 corrective re-dispatches, orchestrator pickup
median 2.2s); ~80% of active agent time is model generation, not tool execution; builder
(opus/high) alone was 63% of all active agent seconds (median 297s, 14k output tokens per
dispatch), scout 95% generation despite being the search role. The user's call, effort
before model per the routing rule: builder high→medium (well-specified work shouldn't
need high-effort breadth; near-zero bounce rate leaves headroom to trade), scout
medium→low (its coverage comes from Grep sweeps, not reasoning — this supersedes the
2026-08-04 "medium is the roster-wide effort floor" call). The style also gains scout
question-batching and verbatim `path:line` forwarding into later dispatches, targeting
builder's 74s median pre-edit discovery phase. Builder→sonnet was considered and
deferred pending evidence at the new tiers.

**Revision — terse register (2026-08-14).** The user wanted the main loop markedly less
verbose. Research pass (community practice + official docs) established the mechanism:
CLAUDE.md is injected as user-turn context inside a "may or may not be relevant"
system-reminder and decays with long context and compaction, while output-style text
lands in the system prompt proper — the structurally correct home for register rules.
Hard length caps rejected: Anthropic's own postmortem reverted a system-prompt word cap
for measurably hurting coding quality, and the 2026-07-27 response-shape decision
(interpretive load, not token count, is the target) stands. The fix is behaviour bans —
the community-converged set: answer on line 1, no pre-announcing, no restating the
request, no dispatch/tool narration, no closing summary or offers to elaborate, fixed
post-change report (files / behaviour / validation / risks) — plus an honesty guard
(brevity never eats bad news) and structure retained where it carries signal. Merged into
the Orchestrator style as a `## Register` section rather than shipped as a separate
`Terse` style because only one output style can be active per session; the register
therefore applies only to orchestrated sessions, and plain sessions keep CLAUDE.md's
Output rules unchanged. A Stop-hook length bounce was considered and rejected (wrong
metric, and the official evidence of harm above); a per-turn `UserPromptSubmit` reminder
is held in reserve if the style alone leaks.

**Revision — one writer per concern, diff budget, narrower review fixes (2026-09-18).**
The layer's fan-everything default was producing the diffs the Layer 2 addendum above
gates against, so four text changes land alongside the two hooks.

`claude/output-styles/orchestrator.md` now splits fan-out by kind: reads, searches and
reviews still go out as a single concurrent wave, but writes are single-threaded per
concern — one builder owns every edit for a feature or fix and receives the whole plan
(files, data flow, where state lives, reuse lines, acceptance criteria). Source: Cognition's
"Don't Build Multi-Agents" and Anthropic's multi-agent research post — parallel writers each
start blind and make conflicting decisions, and coding has fewer genuinely parallelisable
subtasks than research does. The Fable cost model is untouched because the fan-out that
made it work (scouts and reviewers) is exactly the half that stays.

`claude/CLAUDE.md` and `claude/agents/builder.md` gain the diff budget: under 500 changed
lines when the change touches complex logic, 800 otherwise, mechanical changes excepted,
else split into reviewable stages and land the smallest coherent one first. Builder's copy
turns it into a stop-and-report rule rather than a target it can quietly overshoot. Source:
OpenAI's Codex repo `AGENTS.md`.

`claude/commands/jun-review.md` narrows the fix wave to clusters whose consequence is a
correctness bug or a gap against what the branch set out to do; style and robustness
clusters are listed as optional findings instead. Source: Anthropic's Claude Code best
practices, which names acting on every reviewer finding as a cause of over-engineering.

`claude/CLAUDE.md` also gains two clauses in the existing rules rather than new sections:
the over-engineering counter-prompt from Anthropic's prompting guide (no fallbacks, error
handling or flexibility that was not asked for — the right amount of complexity is the
minimum the task needs), and a root-cause requirement for visual bugs (name the layout
model, container or rule that is wrong before editing; a margin or breakpoint nudge that
fixes one case is a symptom patch).

**Addendum (2026-09-21) — continue the same writer.** Follow-ups within a concern (a
fix, the next stage, review findings) continue the writer agent that made the change via
SendMessage rather than dispatching a fresh one. A fresh agent re-gathers context and
re-decides, which is exactly the divergence the single-writer rule exists to remove; the
orchestrator style now states this as the default, with a new writer reserved for a new
concern or a writer that no longer exists.

**Addendum (2026-09-21) — docs first.** Sessions were starting from code even in projects
whose codebase is mapped in the Tolaria vault, because nothing loaded at session start said
the map existed. Fix in two places: a `## Docs first` section in each mapped project's
CLAUDE.md naming the index note (Cellular first: `Work/Cellular/ux-flow-index.md`), and one
orchestrator sentence making scout dispatches carry the relevant note paths. A SessionStart
hook injecting the index is deferred until the rule is seen to decay, per the governing
principle.

**Rules out.** Spec-driven frameworks (Spec Kit, Kiro) — Thoughtworks' assessment is more
ceremony for no smaller diffs, and the diff budget plus the quality gate target the outcome
directly. Moving all writes back into the main session: single-writer is about one writer
per concern, not about who that writer is; putting edits on the Fable main loop defeats the
whole cost model Layer 5 exists for.

## Layer 1 addendum — length licence removed, discuss→approve restored (2026-08-14)

Companion to the terse-register revision above, same session. Three changes to
`claude/CLAUDE.md`, one to the register:

1. *Output first line* — the 2026-07-27 clause "not brevity: a longer structured answer
   beats a shorter dense paragraph" was being read as a licence to expand every answer.
   Replaced with "low interpretive load in the fewest words that carry it: structure
   beats dense prose, and neither pads". Interpretive load stays the target metric; only
   the length licence goes. Rationale for keeping this in CLAUDE.md despite the register:
   CLAUDE.md reaches plain sessions and subagents, which output styles never do, and
   style+CLAUDE.md redundancy is the documented compliance pattern.
2. *Bulleted summaries* — new Output bullet: summarise in bullet points by default; the
   user parses a bulleted summary faster than a prose paragraph.
3. *Discuss→approve* — the user observed Fable drifting to act-first-report-later, away
   from their discuss/approve workflow. Traced to two instruction sources, not learning:
   the old "state assumptions, then proceed; stop only when you can't continue" bullet
   (proceed-by-default with a near-unreachable stop bar) compounded by harness-level
   autonomy directives in recent Claude Code. The bullet is split: unspecified edits get
   proposed first (files, shape, one-line why) and await go-ahead — questions and "have a
   look" are discussion, not authorisation; approved or precisely-specified changes
   proceed without re-asking within that scope. Accepted trade-off, the user's call: one
   extra approval on turns where immediate action was wanted.
4. *Register guard* — one clause added to the Orchestrator `## Register` so "don't
   announce what you're about to do" reads as banning execution narration, not as
   overriding the approval gate.

## Layer 1 addendum — plan drift recorded in the plan doc (2026-09-02)

Repeated-workflow admission (3+ occurrences). In long sessions the user plans an
implementation, then makes on-the-fly calls during the build — a rejected approach, a
taste decision, a scope trim — and had to tell the orchestrator every time to note them
in the docs so the next touch of that area knows about them.

**Decision.** One bullet under `### Execution` in `claude/CLAUDE.md`: when implementation
departs from the agreed plan or settles something it left open, record what changed, why,
and what it rules out in the plan doc (nearest committed doc for the area as fallback)
before reporting done. Plus one clause in the Orchestrator `## Register` ship-report
checklist ("any plan deviations with where they were recorded") so the report can't be
completed without having done it.

Placement rationale: CLAUDE.md because the drift happens in plain sessions too, not only
under the Orchestrator style; the register clause because a checklist item is
self-enforcing where a standalone rule is not. Not a hook — a hook cannot tell a design
decision from a mechanical step. Not a skill — always-on behaviour, not situational
reference. The plan doc is the recording target because it is the file the next session
reads before touching the area, so the deviation sits beside the plan it overrode; this
matches the existing "PLAN.md in the repo, memory is only a pointer" convention.

## Commands addendum — /jun-review (2026-09-02)

**Need.** The user runs three reviewers on a branch — `/blast-radius` (omissions),
`/tidy` (quality), CodeRabbit (bugs) — and then fixes what they find. Run separately, each
reviewer fixes or reports in isolation: `/tidy` applies its own fixes before CodeRabbit
has looked, CodeRabbit's skill fixes as it goes, and one root cause reported by two
reviewers gets patched twice or at the wrong altitude. The orchestrator never sees the
three sets side by side, so the user was sequencing the reviews and the interpretation
by hand each time.

**Decision.** `claude/commands/jun-review.md` — a gather → interpret → eliminate
pipeline driven by the main loop. Reviewers are findings-only: CodeRabbit runs as a
background CLI call (`coderabbit review --agent --base <base>`, deliberately not via its
skill, whose autonomous-fix step is the behaviour being removed), `/blast-radius` is
already report-only, `/tidy` is stopped after its Phase 1. The main loop merges, clusters
by mechanism rather than line, ranks by consequence, spot-checks severe claims, then
dispatches one tiered agent per cluster (`patch` / `builder` / `deep`) in a single wave
with the findings verbatim. Verification is tests/typecheck plus one CodeRabbit re-run,
no loop. Fix gate: auto-apply, skipping only behaviour-changing or false findings — the
user's choice 2026-09-02, matching `/tidy`; "outside the diff" is explicitly not a skip
reason because blast-radius findings are outside the diff by construction. The main loop
drives all three rather than three parallel subagents because subagents cannot spawn
subagents: blast-radius would lose its sweep/classify fan-out and tidy would degrade to
single-pass.

**Side change.** `blast-radius.md` had only ever lived in `~/.claude/commands/`, never in
the repo; copied into `claude/commands/` unchanged so the install ships everything
`/jun-review` depends on.

**Governing-principle justification.** Passes on the repetition bar: the
three-reviewers-then-fix sequence was being typed by hand every time, and the holistic
interpretation step — the thing the command exists for — is a workflow no single reviewer
can perform.

## Commands addendum — /tidy (2026-07-29)

**Need.** The built-in `/simplify` reviews the diff on four angles (reuse, simplification,
efficiency, altitude) but none of them covers the user's self-explanatory-code policy
(CLAUDE.md `## Code style`): a comment is a symptom that the code failed to explain
itself, and the fix is restructuring first, deletion second — which he was correcting by
hand. The built-in is compiled into the Claude Code binary, so it cannot be edited or
extended in place.

**Decision.** `claude/commands/tidy.md` — a fork of `/simplify` v2.1.220 with a fifth
Self-explanatory-code angle. Phases 0–2 and the four original angle texts were extracted
verbatim from the binary (provenance: `~/.local/share/claude/versions/2.1.220`, American
spelling preserved); the fifth angle is new and encodes the CLAUDE.md comment rule with
the user's 2026-07-29 refinement: restructure the code (rename, extract, de-clever) until the
comment has nothing left to say, then delete; deletion alone only for comments with no
information to fold back in; a kept comment is a one-line non-recoverable why; match
surrounding density; don't touch comments outside the diff. Named `/tidy` rather than
`/simplify` because shadowing behaviour between user commands and built-in skills is
undefined — a distinct name is deterministic. The official `code-simplifier` plugin was
evaluated and rejected as the vehicle: it is a single edit-as-it-goes agent (no fan-out,
no findings/apply separation) with another repo's style rules hardcoded; this fork makes
it redundant.

**Governing-principle justification.** Passes: the self-explanatory-code failure is caught
by nothing else deterministically (the built-in's angles miss it; the CLAUDE.md rule is
probabilistic prose), and the fix rides an already-proven command shape rather than adding
a new component class.

## Removed — plan gate; Output/tables reframed as intent; /fan slimmed (2026-07-28)

Second pass of the Claude 5 audit, applied after reading Anthropic's context-engineering
article for Claude 5-generation models ("rules → judgement"; "examples constrain
exploration"). The user explicitly chose the article's guidance over the 2026-07-27 shape
eval — the eval sections above stand as history, but their "keep the 10 rules" conclusion
is superseded by this decision, not by a counter-measurement.

- **Plan-gate prompt hook removed** (PreToolUse/`ExitPlanMode`, both settings copies).
  The six-axis presence check forced six notes of assessment boilerplate onto every plan —
  exactly the mandated-verification pattern Anthropic reports causes over-verification on
  Claude 5 models. The 2026-07-08/27 addenda above record its design and its always-open
  revalidation condition; that revalidation is now moot.
- **`## Output` rewritten as intent-based preferences.** Countable caps (5-item lists,
  3-sentence paragraphs, one-caveat) and "never …" phrasing replaced by the intent they
  encoded: scannability and low interpretive load over brevity, structure over dense prose,
  lead with the outcome, scale to the answer. Substance retained, prohibition dropped.
- **`## Markdown tables` collapsed to one preference line** with an explicit
  unless-I-ask-for-it escape, closing the conflict with prompts that request such tables.
- **`/fan` cut from 3,068 to ~1,000 bytes.** The "Shapes to reach for" catalogue and most
  rules paraphrased the Workflow tool description; the command now carries only what it
  uniquely provides — the explicit opt-in, the don't-shrink-the-structure mandate, and the
  adversarial-verification requirement.

## Removed — harness-duplicated components (2026-07-28)

From an audit of the config against the Claude 5-generation harness, whose system prompt and
tool descriptions now carry material this config was written to supply. Each removal fails the
governing principle post-harness-change: the harness catches it deterministically, so the config
line caught nothing extra.

- **`session-context.sh` deleted** (script + `SessionStart` wiring, uninstall.sh entry). The
  harness now injects an identical branch / dirty-state / recent-commits block at session start —
  both copies were observed side by side in a live session. ~80 duplicated tokens per session.
- **CLAUDE.md `## Routing` deleted** (Skills / Search / External tools, 649 bytes). The Skill
  tool description instructs skill delegation, and the harness's own guidance covers search-tool
  and LSP routing. The todo-tool `### Execution` rule went with it — task-tool reminders carry
  that behaviour, and the rule named a tool that no longer exists under that name.
- **Comments rule reframed from prohibition to context.** "Do NOT add comments" contradicted the
  harness's "match the surrounding comment density" and this config's own edit-surface rule in
  comment-dense files (including our own hooks). Now: match surrounding density; when in doubt
  prefer none; a new comment is a one-line non-recoverable WHY only.
- **Deny `Bash(curl:*)` narrowed to the four mutating `-X <verb>` forms.** The blanket entry made
  `safety-bash.sh` rule 7 (mutating HTTP) unreachable dead code and blocked read-only curl
  (health checks, header inspection). The hook remains the real enforcement across flag orderings;
  the deny entries are belt-and-braces for the common literal forms only (`-XPOST`, `--request`
  and `-d` variants rely on the hook).

Deliberately **not** removed in the same audit: the `## Output` section (2026-07-27 eval evidence,
above), the plan-gate hook (open item — re-eval on the current planner generation before touching),
and the CLAUDE.md git-safety line (kept as an intent signal; the hook and deny list enforce it).

## Changed — `.env` read guard moved from deny rules to hook (2026-09-03)

`settings.json` no longer ships any `Read()` deny rule; `safety-files.sh` now also matches the
Read tool and blocks the same secret paths it already blocked for Write/Edit.

Trigger: Claude Code 2.1.259 (auto-updated 2026-09-03 10:21) added a guard — changelog: "`grep -r`/
`cp -r` over a directory holding a denied file now asks". With `Read(./.env.*)` configured and
`.env.local` at every repo root, every `grep -rn … .` became an approval prompt. Verified headless in
auto mode on Sonnet: root grep → "requires approval"; the same grep scoped to `components/` → allowed;
`rg`, `--exclude`, and a `Bash(grep:*)` allow rule do not bypass it (the guard outranks allow rules,
like protected-path writes). Ask rules resolve before the classifier, so auto mode cannot absorb them,
and subagent asks surface as prompts in the parent session — which is where it was felt first, since
scout/builder read via Bash.

Why hook not narrower globs: the deny list was belt-and-braces by design (Layer 2 principle above);
any surviving `Read()` rule still arms the guard for a bare `.env`, and the hook already carried the
secret-path list. Cost: a hook is exit-2 block, not ask, so a secret read cannot be approved through —
the user reads it outside the agent, same contract as `safety-bash.sh`. `.env.example` is blocked
too, unchanged from the old `Read(./.env.*)` rule. Upstream: anthropics/claude-code#91690 tracks the
guard's behaviour; revisit if a later release lets allow rules override it.

**Addendum — the guard fires on any `Read()` deny in effect, not only the shipped one
(2026-09-04).** A project-local `settings.local.json` carrying `Read(//…/tolaria/…)` denies
(client/personal note separation — a legitimate local addition, kept) re-armed the same guard for
that repo. The prompt this time was `cd <repo> && grep … <relative path>`: after a `cd` the engine
cannot resolve the relative path against the denied set, so it asks. Fix on the command shape, not
the rules: all four roster agents now carry "use Grep/Glob/Read for searching and reading, never
`cd` in Bash, always absolute paths" (the Grep tool takes an absolute `path` and resolves cleanly;
subagents already start in the project cwd so the `cd` was redundant). Scout's softer "Bash is for
ls/git/wc" line had already been ignored once, hence the explicit failure named in the rule.
Considered and deferred: an exit-2 bounce in `safety-bash.sh` for `cd` + relative-path compounds —
deterministic, but costs a wasted agent turn per hit and a hook run per Bash call; add only if the
instruction doesn't stick.

## Changed — breakdown trigger widened; Register audience line (2026-09-03)

Evidence: 26 "explain it simply / in bullet points" re-asks in `history.jsonl` since 2026-08-10
(~1 per working day), all in Orchestrator-style sessions. Reading the reply before and after three
of them: the preceding reply was never a malformed explanation — it was a work report (CodeRabbit
triage scoreboard with 64-word paragraphs and four headers; "briefs are above" where the briefs were
builder dispatch prompts; a wave status update). The reply *after* the re-ask landed every time and
shared one shape: bold name line, then `Problem / What you'd see / Fix`, no headers, plain-English
consequences. So the format works; the model wasn't treating reports as explanations, and the
Register's "write like a terse engineer" set the audience to an engineer — the register the user
kept asking it to translate out of.

Two wording changes, no relocation (per the 2026-07-30 trial note: adjust wording before moving):

1. `claude/CLAUDE.md` `### Breakdown format` — header and trigger widened to triage, review
   findings, plan summaries, blockers, and status reports; the `Problem / What you'd see / Fix`
   shape added as the worked example for sets of findings.
2. Orchestrator `## Register` — "terse engineer, not a narrator" replaced with an audience line:
   write for the user, every item carries its plain-English consequence; terse cuts narration, not
   the gloss. The ship-report checklist is unchanged.

Measure: re-count re-asks from `history.jsonl` after a week. If not clearly down, run the
shape-eval harness with Orchestrator on/off as arms, two trials minimum (see "Resolved — response
shape").

## Changed — reuse check made an artefact (2026-09-08)

Observed failure: helpers hand-rolled that the project, stdlib, or an installed dependency
already provided — parsing, retries, formatting, config, HTTP — written fresh instead of called.

Root cause, two halves. The `### Scope and completeness` rule in `claude/CLAUDE.md` said to
"check" before writing a utility: a mental step with no required output, so nothing ever showed
whether it ran. And under Layer 5 the writing happens in subagents that start blind — `builder`
and `patch` never received the check at all, and a dispatch prompt reading "add X" gives a blind
agent no reason to look for X first.

Fix: make the check produce an artefact at each of the three points.

1. `claude/CLAUDE.md` `### Scope and completeness` — wording now demands a named provider or an
   explicit "searched and found none", plus the observation that the capability almost always
   already exists.
2. Orchestrator `## Routing` — a dispatch that adds new code must carry the `path:line` of the
   thing to call or the line "scouted for <capability>: none found"; without it a reuse scout is
   the first wave, not an optional one.
3. `claude/agents/builder.md` and `claude/agents/patch.md` — each agent Greps for an existing
   equivalent before adding a helper, and the report carries a `Reused: <path:line>` /
   `Wrote new: … none found` line (terser in `patch`, whose changes are tiny by definition).

Deferred: a `comment-suspects`-style Stop hook nominating new top-level definitions whose names
collide with existing symbols. It fails the governing principle for now — the prompt-level fix
above is untested, and a hook that catches what three layers of wording already catch earns
nothing. Revisit only after three recurrences post-change show the wording insufficient.

Addendum (2026-09-09) — review-time counterpart. The three prevention points above run
per dispatch and start blind; the branch-level catch-net is `/tidy`'s Reuse angle, which
`/jun-review` already runs as a findings-only gatherer in its Phase 1. That angle had the
same flaw as the old CLAUDE.md wording — it searched by name and neighbourhood, never the
manifest or stdlib — and no angle covered premature abstraction (Altitude flags the
opposite). Renamed "Reuse and abstraction" in `claude/commands/tidy.md`: the same search
recipe the agents will use (manifest → capability synonyms → stdlib), duplication against
code outside the diff, single-use abstractions, and scope that includes SQL, migrations,
database policies and config. Rejected: a fourth `/jun-review` reviewer — it would overlap
tidy:reuse and fail the governing principle. Also rejected: orchestrator-side verification
of every `Wrote new` claim — this branch-level check does that once instead of per dispatch.

Addendum 2 (2026-09-09) — trigger and recipe. The 2026-09-08 wording fired on code shape
("adds a function, module, or helper") but the observed failure is capability-shaped: a retry
loop or parser hand-rolled inline in an existing function adds no helper and never tripped the
rule. All four prompt sites now trigger on the capability (parsing, retries, formatting,
validation, config, HTTP, caching, auth checks), helper or inline, and share one search recipe
— manifest → project by capability synonyms → stdlib — so `builder`, `scout` and `/tidy` look
in the same places. Orchestrator gains the stance that the capability is assumed to exist and
writing it needs "none found" evidence first. `scout` gains a reuse-question bullet — it had
no method for one, so the "reuse scout first wave" had nothing to run. `builder` trusts a
dispatch that carries `Reuse: <path:line>`, double-checks a "none found" with one Grep, and
flags a dispatch that carries neither, removing the duplicate search the 2026-09-08 wording
forced on every dispatch. `deep` deliberately unchanged: it recommends rather than writes, and
its recommendations route through the orchestrator's rule.

Addendum 3 (2026-09-10) — UI knobs and the completion gate. First post-change evidence: a
findings-only deep review of an uncommitted phone-layout rebuild (bippi, `UI/devices-clean`,
~12 dispatches) found six misses, four of them a prop, a variant, or a class cluster — surfaces
the capability list never named — and five of six originating in the orchestrator's dispatch
prompt, which prescribed exact classes to keep patch prompts self-contained and so overrode
conventions the code already documented in comments. Changes: the trigger now names UI knobs
(prop on a shared component, new exported component, class cluster mimicking a variant) in the
orchestrator, `builder`, `patch` and `/tidy`; dispatches describe the outcome and name the
reference, prescribing implementation only when no precedent was found; extraction dispatches
and `builder` carry a sibling Grep for the distinctive string; `patch` and `builder` refuse to
add unnamed props to shared components and report callers instead; `scout` quotes the comments
beside a slot, where conventions live; and the orchestrator's Report section gains a completion
gate — one `deep`, findings-only Reuse-and-abstraction pass over the whole branch diff before
"done" on work that touched a shared component or ran three or more dispatches. The audit's own
numbers: one review dispatch versus four fix patches. The Stop hook for new exported props or
components without a Reuse note stays deferred: this is recurrence one of the three the
Deferred paragraph requires.

## Changed — em-dash rule split by surface (2026-09-09)

Observed: em-dashes appearing in end-user-facing strings — UI copy, hint text, page meta
descriptions, emails. The user wants them kept for internal and developer-facing text
(comments, docs, commit messages, agent reports) and banned from anything an end user could
see.

Placement: one full bullet under `## Language` in `claude/CLAUDE.md` so the main loop carries
it, plus a one-line mirror in `builder`, `patch` and `deep` because subagents start blind.
`scout` skipped: read-only, never writes user-facing text. The Orchestrator style is
unchanged — the agents hold the rule themselves, so dispatches need not forward it. The
replacement instruction is deliberately "a grammatically correct replacement", not a fixed
list of punctuation, on the user's call.

## Added — flow-altitude rule and `/flow` command (2026-09-10)

Observed: the user reports asking Fable to "dumb it down" on more answers than not. Their need
is the mechanism — where data comes from, how it is fetched, compared, stored and shown — not
the code; `/jun-review`, the hooks and the built-in commands already cover the code side.

Diagnosis: the two breakdown-format edits (2026-07-30, 2026-09-03) fixed shape, not altitude —
the "fact — gloss" chain was still built from files and functions. And orchestrator context is
full of agent `path:line` findings with nothing keeping them out of answers to the user.

Fix, two parts:
1. `claude/CLAUDE.md` Breakdown section — a default-altitude bullet: explain at flow level; name
   a file or function only when asked "where in the code" or when the answer is a code change;
   agent `path:line` stays in dispatches and verification.
2. `claude/commands/flow.md` — `/flow [<topic>|<base ref>]`: re-explains the previous answer, a
   topic, or a branch's changes (before → after) as numbered stages — source, fetch, transform
   or compare, store, surface — in about 150 words, ASCII diagram when the flow branches,
   optional "where to look" paths at the end. Passes the Layer 3 workflow bar on the user's
   reported repetition; nothing deterministic can catch an altitude problem.

Measure as with the breakdown trial: re-count "dumb it down" / "high level" re-asks in
`history.jsonl` after two weeks. If the rule alone drops them, `/flow` stays as the branch
explainer; if not, the Breakdown section is the next candidate for compression.

## Changed — /tidy reviewers read the diff whole; post-fix reuse pass on scout (2026-09-14)

Observed: a cost audit of one 44-minute orchestrated session ($48 API-equivalent) found six
`deep` dispatches — /tidy's five angle reviewers plus the post-fix reuse pass — at ~$15, the
largest line after the main loop. Effort was not the driver: output was ~$2 across the six;
cache writes (~$5) and cache reads (~$8) were. Each reviewer ingested the same 35k-token diff
in 400–500-line `sed -n` slices plus 20–40 further Bash reads of source, running 18–33 turns at
130–176k context. The slicing came from the dispatch prompt ("read it in chunks with sed -n")
and from auto mode's harness text preferring Bash, both overriding deep.md's use-Read rule.

Fix, two parts:
1. `claude/commands/tidy.md` Phase 1 — reviewers are handed the diff path and told to load it
   whole with Read (two calls at most), never in slices, explicitly overriding the session's
   shell preference. Turns roughly halve, and reads scale with turns.
2. `claude/output-styles/orchestrator.md` completion rule — the post-fix reuse pass runs as one
   `scout` dispatch instead of `deep`. "Does this capability already exist" is a search
   question, scout's stated job, at ~$0.30 instead of ~$1.80. The pass stays independent of
   builder's own Reused/Wrote-new report line, which is why it was not folded into the fix wave.

Deferred: retiering the five angle reviewers off `deep`. The roster has no review-shaped agent
at high effort — builder's prompt says implement, deep's effort is pinned in frontmatter, and
the Agent tool has no per-call effort knob — so a ~$1 saving does not pass the governing
principle for a new agent. Revisit if reviews still dominate after part 1. Rejected: dropping
deep's effort to `high` globally (touches real debugging to move ~13% of review cost), and
deleting the sixth pass (loses the independent check).

## Changed — /jun-review fix wave gated by a scope test (2026-09-17)

Observed: `/jun-review`'s Phase 2 said "'outside the diff' is not a reason to skip", written
in the 2026-09-02 addendum above to protect blast-radius findings, which are outside the diff
by construction. Unqualified, it licensed every out-of-diff finding — including `/tidy`'s
reuse angle ("the same pattern exists in N other files"), whose own Phase 2 scope guard
`/jun-review` bypasses by stopping tidy after Phase 1. A UI-only branch had unrelated files
edited by the fix wave as a result.

Fix, in `claude/commands/jun-review.md`: a two-rule scope test in Phase 2. The fix wave may
edit files in the branch diff, and files outside it only where blast-radius returned a
`Needs update` verdict with its consequence sentence — a consumer that now behaves wrong,
fixed no further than that. Everything else is reported as an own-branch follow-up. Phase 3
checks each lane's target files against the test before dispatch and carries the allowlist in
the dispatch prompt, with the instruction to stop and report rather than edit outside it.
Phase 4's report splits into in-diff fixes, consumer fixes, and follow-ups.

Rules out: call-site migrations onto a new helper and sibling-pattern fixes as review fixes —
they are refactors and belong to their own branch. Rejected: a durable follow-ups file. The
follow-ups are report-only for now; a new component has not earned its place under the
governing principle until the reporting proves insufficient.

## Added — /jun-project-setup (2026-09-21)

**Need.** Per-project guardrails — a docs-first pointer into the vault map, `lint` and
`typecheck` scripts for the quality-gate hook to have something to run, and size and
complexity rules baselined to the tree as it stands — were being set up by hand, project by
project. The first run on Cellular surfaced four gotchas worth freezing: the project
`CLAUDE.md` may be git-ignored (the pointer then lives on that machine only, which the
report has to say); baselining is not optional (195 files over 300 lines, 2,993 arbitrary
bracket values — unbaselined rules turn the whole tree red and get disabled the same day);
the bracket ban is unusable without an allowlist (`data-[…]`, `aria-[…]`, `group-data-[…]`,
`env(safe-area-inset…)`, `calc(…)`, `var(--…)`); and dependency adds are blocked by
`safety-bash.sh`, so any plugin-based check must be report-then-rerun rather than installed
in-flight.

**Decision.** `claude/commands/jun-project-setup.md` — survey → propose → approve → one
builder. One read-only `scout` measures scripts, ESLint version and rules, Tailwind
brackets and inline styles, file sizes, docs size and whether a vault map exists; the main
loop prints a gap table (Present? / Measured / Action) and the exact content it intends to
write, then stops for approval; one `builder` applies the approved steps add-if-missing,
runs `--suppress-all` to write the baseline on ESLint ≥ 9.24 (rules as `warn` below that),
and verifies lint and typecheck at exit 0. Packages are never installed — the report
carries the exact commands for the lockfile-detected manager, and the second run, after the
user installs, is the intended path for the Tailwind, sonarjs, jscpd and knip checks. JS/TS
only: without `package.json` the command says so and stops.

**Governing-principle justification.** Passes the repetition bar: the same setup runs once
per project, and the four gotchas above are exactly the kind that get rediscovered by hand
each time. It adds no new component — no hook, no skill, no plugin — and installs nothing
the existing hooks do not already need; `quality-gate.sh` is silent in a project with no
`lint` or `typecheck` script, and this is what gives it something to gate on.

**Rules out.** Auto-installing packages, in-flight or otherwise — the hook block is the
design, not an obstacle. A one-size config for non-JS stacks; the manual-setup note is the
answer there until a second stack earns its own path. And the command deciding design
questions: a top bracket pattern like `text-[10px]` ×1007 is reported as a missing type
scale for the user to name, never fixed or configured away.

**Addendum (2026-09-21) — install pause.** The first design deferred the plugin-based
checks (Tailwind bracket ban, sonarjs, jscpd, knip) to a second run after the user installed
them by hand; the Cellular survey showed all four were genuine gaps, so the second run
would be the common path. The command now pauses after the proposal with the exact install
line and a one-line explanation per package, and the user runs it with the `!` prefix
in-session; the run then continues to write the plugin configs. Rules out: allowlisting
those packages in the safety hook so the command installs them itself — the
never-auto-install rule stays intact, and the cost of the pause is one paste.

## Changed — guardrails moved out of the repo into a local lint kit (2026-09-21)

**Need.** The user commonly works in repos they do not own. The 2026-09-21
`/jun-project-setup` design wrote eight files into the project — ESLint rules, plugin
dev-deps, a committed suppressions baseline, jscpd and knip configs, `lint:*` scripts —
and relied on CI to run two of them. That is a team decision made unilaterally, and it was
reverted from Cellular's `development` the same day. The committed baseline also failed
on its own terms: generated from one tree, it made every branch that diverged earlier
look entirely new — 364 "new" errors in the trips worktree, nine Stop-gate bounces at
~30 s each, then the runaway override. The checks are for the user's agent sessions, not
for the repo.

**Decision.** A lint kit under `claude/lint/`, installed to `~/.claude/lint/`.

- *Kit.* Its own `package.json` (eslint, typescript-eslint parser, eslint-plugin-sonarjs,
  eslint-plugin-better-tailwindcss, jscpd, knip) and one flat config carrying the size,
  complexity, depth, params, cognitive-complexity and bracket-ban rules with the existing
  allowlist. Run with `--config <kit> --no-config-lookup`, so the project's own ESLint
  config is neither read nor edited. `install.sh` copies the kit and prints the dependency
  install line; it never runs it. `kit.sh` is the single entry point (`paths`,
  `installed`, `baseline`, `check`, `dupes`, `dead`) that hooks and commands call.
- *State, two keys.* Settings (Tailwind theme path) are keyed per repo — sha1 of the
  resolved `git rev-parse --git-common-dir` — so every worktree of a repo shares them. The
  suppressions snapshot is keyed per worktree — sha1 of `git rev-parse --show-toplevel` —
  so a branch only competes against itself. Both live under `~/.claude/lint/projects/`.
- *Snapshot at SessionStart.* `claude/hooks/lint-baseline.sh` (SessionStart) takes the
  worktree's snapshot when none exists. Session start is before any agent edit, so the
  snapshot is the user's code by construction. Zero tokens, no command to run per
  worktree.
- *Gate.* `quality-gate.sh` keeps running the project's own `lint` and `typecheck`
  unchanged — the team's rules — and adds `kit.sh check` over files changed since HEAD
  plus untracked, against the worktree snapshot. A violation above the snapshot blocks
  with exit 2 as today. jscpd and knip stay out of Stop: whole-project checks belong to
  review.
- *Review.* `/tidy`'s Duplication bullet and `/jun-review` Phase 4 run the kit's `dupes`
  and `dead`, falling back to a project's own `lint:*` scripts where the repo defines
  them (the earlier 2026-09-21 `lint:*` rule stays as that fallback).
- *Setup.* `/jun-project-setup` keeps its survey and gap table. Apply writes only the
  per-repo settings file and the docs-first pointer into `CLAUDE.local.md`, added to
  `.git/info/exclude`. Removed: the install pause, package and config edits, the
  committed baseline, and the `lint:*` scripts. Runs once per repo. Report states that no
  repo file changed.

**Governing-principle justification.** No new enforcement surface — the same Stop gate,
the same rules — relocated so it can exist at all in a repo the user cannot change. The
per-worktree snapshot catches a failure the committed baseline caused rather than caught:
pre-existing code on a diverged branch being reported as new. The SessionStart snapshot is
a hook because a stale or missing baseline is a deterministic condition; asking the model
to remember to take one is the advisory pattern the Layer 2 addendum exists to replace.

**Rules out.** Copying a snapshot between worktrees (the exact mismatch that failed
today). An "own project" mode that writes into the repo — a team gate is a hand-made PR.
Editor integration: the rules show in the editor only when the repo carries them, and
that cost is accepted. A bounce cap in the gate: with attributable failures the loop
converges in one round; the eight-block override stays the backstop, and the bounce log
is the evidence for revisiting.

**Resolved in the build (2026-09-21).** All three plugins run clean from the kit against a
foreign project: better-tailwindcss resolves the project's own `tailwindcss` from cwd, so
the kit carries none; jscpd 5.x has a native baseline (`--baseline`, `--update-baseline`,
`--fail-on-new-clones`), so `dupes` uses it rather than a hand-rolled diff; knip reports
from an external config. Four decisions the build settled:

- *Inline disables are ignored.* The kit config sets `noInlineConfig`. The project's own
  `eslint-disable` comments name plugins the kit does not load, and ESLint reports each
  as an error attributed to the missing rule — 177 phantom entries in the first snapshot,
  and a guaranteed unfixable block the next time a changed file gained one. The side
  effect is the rule the gate message already states: an inline disable cannot silence a
  kit rule. `--quiet` drops the resulting per-directive warnings; lossless because every
  kit rule is `error`.
- *`check` passes `--pass-on-unpruned-suppressions`.* ESLint otherwise exits 2 whenever
  the snapshot holds entries the run did not see — every run over a handful of changed
  files, and every time a suppressed violation is genuinely fixed. The snapshot is
  rewritten only by `baseline`; `--prune-suppressions` is never passed.
- *`dupes` reports a count, not locations.* jscpd's new-clone check is count-only and its
  console reporter ignores the baseline, so the compare runs silent and prints the
  command to see the clones when it fails. Rules out parsing the full clone report to
  diff it by hand until the count-only answer proves insufficient in use.
- *Settings are created on first use.* `baseline` writes the per-repo settings file when
  absent, auto-detecting `tailwindEntry` from the common `globals.css` locations, so a
  worktree the setup command never ran in still gets the bracket rule. `/jun-project-setup`
  remains the place to correct the path.

Measured on the trips worktree: snapshot 8.6 s (4502 suppressed, 587 files); `check` on
three changed files ~1 s; SessionStart hook 134 ms when the snapshot exists. The gate's
jscpd json reporter was removed after it wrote a report file into the project — the one
invariant the design exists to protect, caught in the first test run.

**Scope of never-auto-install (2026-09-21).** The rule stays absolute where it was written
to bite: dependencies added to a project the user may not own, and third-party binaries
fetched on their behalf — the language servers stay check-and-report for exactly that
reason. The kit is neither. It is first-party, it lives under `~/.claude`, and it installs
from its own committed lockfile with `npm ci`, inside a script that already overwrites the
user's `settings.json`, hooks and CLAUDE.md. Leaving one paste-this line as the price of a
fresh machine bought no supply-chain safety it did not already have. So `install.sh` runs
it, and prints the manual line only as the fallback when `npm` is missing or `npm ci`
fails; the install never aborts over the kit.

## Removed — default model pin (2026-07-27)

`settings.json` no longer ships a `model` key. The config is model-agnostic by design: the
user picks the model per task (`/model`, which persists their own default), and a shipped pin
silently overwrote that choice on every reinstall — which happened in practice the day this
was removed. Everything the config enforces (hooks, deny list, plan gate, output rules) is
written to work on any model; the only pinned model anywhere is the plan-gate judge
(`claude-sonnet-5`, alias form), which is a hook implementation detail, not the user's
working model. Model-conditional tuning decisions (effort, rule deletions) go through the
eval kit against whichever model the user actually runs, not through shipped defaults.

## Removed — LEARNINGS.md (2026-07-27)

The manual lesson-capture log shipped in May was deleted from the repo and the installed
config: zero entries in ten weeks, and Claude Code's auto-memory now captures the same
material with less friction. The promote-to-CLAUDE.md loop it existed for never ran once,
so the component fails the governing principle — it caught nothing that nothing else
catches. `install.sh`, `uninstall.sh`, and the README were updated to match.

---

## Layer 1→3 — Tolaria routing moved to a skill (2026-07-27)

The "Markdown lives in two places" block (5 lines, ~700 bytes) was removed from `CLAUDE.md`
and reinstated as `claude/skills/notes-routing/`. It is routing knowledge that only applies
when the user asks where something was tracked, but it was loading in every session of every
project. A path-scoped `.claude/rules/` entry was rejected: rules trigger on file paths, and
this triggers on a *question type*, so a scoped rule would never fire.

**Principle amendment.** Layer 3 previously admitted only repeated workflows. It now also
admits situational reference material displaced from CLAUDE.md. The workflow bar is
unchanged — this widening covers content that already earned its place, only at the wrong
layer, and does not license new workflow skills below the 3+ repetition bar.

**Cost.** ~175 tokens per request always-on becomes ~25 tokens (the description) plus an
on-demand body load. The saving is small; the reason to do it is that Tolaria-specific
routing was loading into unrelated projects. `install.sh` (skills dir + per-skill copy),
`uninstall.sh` (targeted removal so a user's own skills survive), the README table and the
repo `CLAUDE.md` layout list were updated to match.

## Layer 1 — verification rules removed (2026-07-27)

Two `### Execution` rules were deleted: "Verify against the success criteria before declaring
done" and "Treat exit 0 as a starting point, not proof of correctness." Anthropic's Opus 5
prompting guidance states that the model verifies its own work unprompted, and that explicit
verification instructions "cause over-verification on Claude Opus 5, and removing them reduces
wasted tokens with no loss in quality." "Run tests/typecheck/lint where applicable" was kept —
it directs which checks to run rather than adding a verification pass on top.

**Open, not closed.** The six-axis plan gate carries the same category of instruction and was
validated on Opus 4.8 in the July benchmark, before this behaviour changed. It is deliberately
left in place pending a re-run on Opus 5. Do not treat the CLAUDE.md deletion as settling the
hook.
