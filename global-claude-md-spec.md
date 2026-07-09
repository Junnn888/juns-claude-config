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
| 1 — CLAUDE.md | Built | Global behaviour rules (~28 lines): surface-uncertainty, scope/completeness, output concision, edit-surface, goal-driven execution, process discipline, safety, British-English, routing. Provenance-traced from Karpathy / gstack / Anthropic guidance. |
| 2 — Hooks | Built | `permissions.deny` list + matcher-scoped hooks: two PreToolUse safety **command** hooks (`safety-bash.sh`, `safety-files.sh`), one PreToolUse **prompt** hook (plan reviewer, below), one SessionStart context loader (`session-context.sh`). |
| 3 — Skills | Deferred | Build only when repetition justifies it (re-explained 3+ times, multi-step with gotchas, needs enforced checkpoints, or needs isolation/model-routing). |
| 4 — LSP | Built | Official first-party LSP plugins (`claude-plugins-official`), 12 languages. Installing one auto-enables Claude Code's built-in LSP tool. Binaries are check-and-report only (never auto-installed — irreducible supply-chain surface). |

### Layer 1 — CLAUDE.md
Behaviour rules only; kept short so it loads cheaply every session. Each rule must change
behaviour the model wouldn't reliably reach on its own. The Coding-plan assessment rubric
(Layer 2 addendum) lives here because it shapes how plans are written.

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

**Two coupled parts:**

1. **Rubric** — `claude/CLAUDE.md` → *Coding-plan assessment*. Any code-changing plan must carry a
   one-line, falsifiable note per axis (simplicity, over-engineering, logic/correctness, UX,
   performance), each naming a concrete concern or a specific reason it's a non-issue. Bare
   "Fine"/"N/A" is not acceptable.

2. **Hook** — `claude/settings.json` → `PreToolUse` / matcher `ExitPlanMode`, `type: "prompt"`,
   `model: "sonnet"`. A single-turn model evaluation that fires at plan-exit and checks only that
   each of the five axes carries a specific, falsifiable note — not whether the plan is *good*
   (it cannot verify performance or correctness against the real codebase). Approves if all five
   are addressed; otherwise denies and lists the missing/hand-waved axes.

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

## Deferred — response verbosity (2026-06-05)

**Symptom.** Under ultracode / high-effort modes on Opus 4.8, responses run verbose — lines of
code snippets that don't change the next action, plus sentence padding — despite the Layer 1
Output concision rules already in `CLAUDE.md`.

**Why deferred, not fixed (decided 2026-06-04 alongside the plan-reviewer work).** Kept out of that
change to protect its scope and keep its test uncontaminated. More fundamentally, a global
`CLAUDE.md` line is the wrong instrument: it loads in *every* session (would over-suppress useful
code in ordinary work) and fights ultracode's own "be exhaustive, token cost is not a constraint"
directive, so it would be weak anyway. The symptom is mode-specific; the fix must be too.

**Intended fix (when built).** Scope it like the plan gate — one crisp, checkable thing, not "obey
all of `CLAUDE.md`":
- an ultracode/effort-scoped nudge — keep exhaustiveness in the *work* (verification, coverage),
  not the *prose*; include a snippet only when it changes the next action; or
- a narrow `Stop` hook flagging only code/padding that doesn't change what the user would do — lean
  advisory to avoid the every-turn latency and `stop_hook_active` loop tax.

**Interim.** Logged as a self-applied preference in Claude's file memory, so output is trimmed
until a mechanism exists.

**Governing-principle status.** Not yet earned as a component; must clear the same bar (crisp,
deterministic where possible, catches a failure nothing else does) before it becomes a hook or rule.
