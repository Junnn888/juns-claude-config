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
| 1 — CLAUDE.md | Built | Global behaviour rules (~76 lines): surface-uncertainty, scope/completeness, output concision, edit-surface, goal-driven execution, process discipline, safety, British-English, routing. Provenance-traced from Karpathy / gstack / Anthropic guidance. |
| 2 — Hooks | Built | `permissions.deny` list + matcher-scoped hooks: two PreToolUse safety **command** hooks (`safety-bash.sh`, `safety-files.sh`), one PreToolUse **prompt** hook (plan reviewer, below), one SessionStart context loader (`session-context.sh`). |
| 3 — Skills | Deferred | Build only when repetition justifies it (re-explained 3+ times, multi-step with gotchas, needs enforced checkpoints, or needs isolation/model-routing). |
| 4 — LSP | Built | Official first-party LSP plugins (`claude-plugins-official`), 12 languages. Installing one auto-enables Claude Code's built-in LSP tool. Binaries are check-and-report only (never auto-installed — irreducible supply-chain surface). |

### Layer 1 — CLAUDE.md
Behaviour rules only; kept short so it loads cheaply every session. Each rule must change
behaviour the model wouldn't reliably reach on its own.

### Layer 2 — Hooks
Matcher-scoped, never global-fire; target <200ms for command hooks; exit 2 for hard enforcement.
The deny-list is belt-and-braces only — Bash deny patterns are fragile and don't cover
subprocesses, so the **hooks** are the real enforcement.

- `safety-bash.sh` — PreToolUse(Bash). Hard-blocks dangerous command categories (git state,
  DB/migrations, destructive FS, deploy, secrets, dep-adds, mutating HTTP, system, CI).
- `safety-files.sh` — PreToolUse(Write|Edit|MultiEdit). Blocks edits to `.env*`, keys, credentials.
- `session-context.sh` — SessionStart. Injects branch + dirty state + last 5 commits.

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

---

## Layer 2 addendum — status line & settings sync (2026-06-25)

**Status line.** `claude/statusLine.sh` renders `model · <n>k tok (<pct>%)` from the harness's
status JSON via `jq`; wired through `settings.json` → `statusLine` (command type, `~/.claude/
statusLine.sh`). `install.sh` copies it to `~/.claude/` and `chmod +x`; `jq` is already a documented
prerequisite, and the script prints nothing without it (graceful degrade, no error).

**Settings folded in from live config.** `model: opus[1m]`, `effortLevel: high`, `tui: fullscreen`,
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
