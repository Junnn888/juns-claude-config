# juns-claude-config

Portable Claude Code configuration repo. Installs a global `~/.claude/` setup via `curl | bash`: locked CLAUDE.md (behaviour rules), deny-list + safety hooks, and official LSP plugins.

## Repo purpose

This repo IS the config. Everything here either gets installed to `~/.claude/` or supports the install/uninstall flow. When developing this config, changes here flow to users via the install script.

## Architecture — layers

The config is built in layers, each with a governing principle: a component earns its place only if it catches a failure nothing else deterministically catches.

| Layer | Status | What |
|-------|--------|------|
| 1 — CLAUDE.md | Built | Global behaviour rules and output preferences. Provenance-traced from Karpathy/gstack/Anthropic. |
| 2 — Hooks | Built | 2 PreToolUse safety command hooks (Bash dispatcher + file-path guard) + `permissions.deny` list. |
| 3 — Skills | Built | 1 skill (`notes-routing`). Principle widened 2026-07-27 to admit situational reference material that would otherwise sit always-on in CLAUDE.md. Workflow skills still need the 3+ repetition bar. |
| 4 — LSP | Built | Official LSP plugins (`claude-plugins-official`), 12 languages. Auto-enables Claude Code's built-in LSP tool. |
| 5 — Orchestration | Built | `Orchestrator` output style (opt-in) + `scout`/`patch`/`builder`/`deep` agent roster pinning model+effort tiers. Scale fan-outs stay behind `/fan`. |

Full design decisions and rationale live in `global-claude-md-spec.md`.

Working config files live under `claude/` and are installed to `~/.claude/`; install scripts and docs sit at root.

## Development principles

- **Governing principle:** a new component (skill, hook, plugin) is built ONLY if it catches a failure nothing else does, OR a workflow is repeated 3+ times with gotchas worth freezing.
- **Supply chain:** prefer first-party/official plugins over third-party. Check-and-report for binaries, never auto-install.
- **Hooks:** always matcher-scoped, never global-fire. Exit 2 for enforcement. Target <200ms per hook.
- **Deny-list is belt-and-braces:** hooks are the real enforcement. Deny patterns are fragile (can't cover subprocesses).
- **No speculative features.** If you're tempted to add something "while we're here," don't. It must pass the governing principle first.

## Adding components

- New skill: validate against the Layer 3 governing principle in `global-claude-md-spec.md`, then record the decision and rationale there.
- New LSP language: follow "Adding a new language later" in README's LSP layer section (install.sh array + doctor row + binary).

## Key references

- `global-claude-md-spec.md` is the source of truth for all design decisions and their provenance.
- GitHub repo: `Junnn888/juns-claude-config` (confirm path placeholders in install/uninstall scripts match).
