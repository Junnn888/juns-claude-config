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
