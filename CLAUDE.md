# juns-claude-config

Portable Claude Code configuration repo. Installs a global `~/.claude/` setup via `curl | bash`: locked CLAUDE.md (behaviour rules), deny-list + safety hooks, session-context loader, and a self-authored LSP plugin.

## Repo purpose

This repo IS the config. Everything here either gets installed to `~/.claude/` or supports the install/uninstall flow. When developing this config, changes here flow to users via the install script.

## Architecture — layers

The config is built in layers, each with a governing principle: a component earns its place only if it catches a failure nothing else deterministically catches.

| Layer | Status | What |
|-------|--------|------|
| 1 — CLAUDE.md | Built | Global behaviour rules (~28 lines). Provenance-traced from Karpathy/gstack/Anthropic. |
| 2 — Hooks | Built | 2 PreToolUse safety hooks (Bash dispatcher + file-path guard) + 1 SessionStart context loader + `permissions.deny` list. |
| 3 — Skills | Deferred | Skills-layer governing principle locked. Build only when repetition justifies it (re-explained 3+ times, multi-step with gotchas, needs checkpoints or isolation). |
| 4 — LSP | Built | Self-authored plugin (`jun-lsp`), 16 languages, zero third-party plugin code. Enabled via `ENABLE_LSP_TOOL=1`. |

Full design decisions and rationale live in `global-claude-md-spec.md`.

## Current repo layout (flat — not yet restructured)

Files at root level. The README documents the intended nested layout (`claude/`, `plugins/jun-lsp/`, `.claude-plugin/`) but the repo hasn't been restructured yet.

- `install.sh` — installs config to `~/.claude/`, backs up existing, runs LSP doctor
- `uninstall.sh` — restores backup or removes installed files
- `settings.json` — permissions.deny + hook wiring + `ENABLE_LSP_TOOL=1`
- `plugin.json` — LSP plugin manifest (pinned version, self-authored)
- `marketplace.json` — self-hosted marketplace catalog
- `global-claude-md-spec.md` — full design spec (layers 1-4, all decisions, provenance)
- `README.md` — user-facing install/usage docs

## Development principles

- **Governing principle:** a new component (skill, hook, plugin) is built ONLY if it catches a failure nothing else does, OR a workflow is repeated 3+ times with gotchas worth freezing.
- **Supply chain:** zero third-party plugin code. Check-and-report for binaries, never auto-install. Pinned versions.
- **Hooks:** always matcher-scoped, never global-fire. Exit 2 for enforcement. Target <200ms per hook.
- **Deny-list is belt-and-braces:** hooks are the real enforcement. Deny patterns are fragile (can't cover subprocesses).
- **No speculative features.** If you're tempted to add something "while we're here," don't. It must pass the governing principle first.

## When adding a new skill

1. Validate against the skills-layer governing principle (see `global-claude-md-spec.md`, Layer 3).
2. The skill must satisfy at least one: genuinely repeated workflow, multi-step with gotchas worth freezing, needs enforced checkpoints, or needs isolation/model-routing.
3. If it passes, add the skill and update `global-claude-md-spec.md` with the decision and rationale.

## When adding a new LSP language

1. Add one entry to the `.lsp.json` server map.
2. Add a matching `lsp_check` row in `install.sh`.
3. Bump `version` in `plugin.json`.

## Key references

- `global-claude-md-spec.md` is the source of truth for all design decisions and their provenance.
- GitHub repo: `Junnn888/juns-claude-config` (confirm path placeholders in install/uninstall scripts match).
