# juns-claude-config

Personal Claude Code configuration. Installs global settings, hooks, permissions, and commands to `~/.claude/`, plus a `/init-project` command that scaffolds project-specific config for any codebase.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

This backs up any existing config before overwriting. Re-run to update.

## What gets installed

```
~/.claude/
  CLAUDE.md                         Global workflow preferences
  settings.json                     Permissions, thinking, hooks
  keybindings.json                  Custom keyboard shortcuts
  hooks/block-git-commit.js         Blocks git commit/add/push in all sessions
  commands/
    block-agent-commits.md          Patches subagent files to prevent autonomous commits
    init-j.md                       Scaffolds project-specific config
    learn.md                        Extracts prefer/avoid patterns from commits
```

### Global settings

- **Extended thinking** enabled with high effort level
- **Git safety**: Hook blocks `git commit`, `git add`, `git push` at the shell level. Deny list also blocks `git reset --hard`, `git checkout .`, `git clean`, `rm -rf`, and `sudo`.
- **Auto-allowed tools**: Read-only git commands, file utilities, Node/Bun/npm commands, MCP tools, Agent, Edit, Write, Task tools
- **Keybindings**: Ctrl+T (todos), Ctrl+O (transcript), Ctrl+B (background task)

### Commands

**`/init-j`** — Run this in any project directory to generate:

- `CLAUDE.local.md` — 30-50 lines of hard rules tailored to the project (tech stack, conventions, key abstractions, common commands)
- `.claude/rules/` — Path-scoped rule files that only load when editing matching files (e.g., migration rules load only when editing `supabase/`)
- `.claude/settings.local.json` — PostToolUse hook for automatic type-checking after edits
- `.gitignore` update — Adds `.claude/rules/` so project config stays personal

**`/learn`** — Analyzes recent commits and extracts coding patterns into `.claude/rules/patterns.md`. Code that was committed is classified as "Prefer"; code that was replaced is classified as "Avoid". Tracks the last analyzed commit SHA so subsequent runs only process new commits. Caps at 15 prefer + 15 avoid entries to stay within instruction budget.

**`/block-agent-commits`** — Patches `~/.claude/agents/*.md` files with a `<git-commit-policy>` block that prevents subagents from running git commit/add/push. Needed because Claude Code hooks don't propagate to subagents spawned via the Task tool.

## Design philosophy

Based on research comparing Claude Code and OpenCode workflows:

- **Instruction adherence is the constraint, not context tokens.** Claude reliably follows ~150-200 instructions; the system prompt uses ~50. Config files stay concise to maximise compliance.
- **Path-scoped rules are free until triggered.** Domain-specific conventions go in `.claude/rules/` instead of a single large instruction file.
- **Hooks are deterministic but not free.** PostToolUse output accumulates in context. Only typecheck is hooked — lint is handled by pre-commit, tests are run explicitly.
- **If Claude can discover it by reading existing files, don't write an instruction for it.** Instructions are reserved for things that cause real breakage if violated.

## Porting to a new machine

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

Then open any project and run `/init-j`.

## License

Personal configuration. Not licensed for redistribution.
