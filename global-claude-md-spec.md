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
| 5 — Orchestration | Built | `Orchestrator` output style (opt-in via `/config`) + agent roster (`scout`/`patch`/`builder`/`deep`) pinning model+effort tiers for delegation. Steady-state delegation only; scale fan-outs stay behind `/fan`. |

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
opt-in and cost control stay with the user. Not enabled by default: `outputStyle` is left
out of `settings.json`; selection is per-user via `/config`.

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
