# juns-claude-config

Personal Claude Code configuration. Installs global settings, hooks, permissions, and commands to `~/.claude/`.

The purpose of this config is to be able to achieve as much of opencode's niceities as possible, while using the claude max plan. Opencode Zen and Openrouter = expenny :(

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

This backs up any existing config before overwriting. Re-run anytime to update.

### What gets installed

```
~/.claude/
  CLAUDE.md                         Global workflow preferences
  settings.json                     Permissions, thinking, hooks
  keybindings.json                  Custom keyboard shortcuts
  hooks/block-git-commit.js         Blocks git commit/add/push in all sessions
  commands/
    j-init.md                       Scaffolds project-specific config
    j-learn.md                      Extracts prefer/avoid patterns from commits
    j-review.md                     Parallel code review + lint check
    j-am.md                         Switch agent models (normal/max)
    j-block-agent-commits.md        Patches subagent files to prevent autonomous commits
  agents/
    code-reviewer.md                Reviews code for bugs, security, architecture (Opus)
    lint-checker.md                 Checks style, naming, conventions (Haiku)
    test-writer.md                  Writes comprehensive tests (Sonnet)
    debugger.md                     Structured diagnosis of complex bugs (Opus)
```

### What the global config does

- **Extended thinking** enabled with high effort level
- **Git safety**: A PreToolUse hook blocks `git commit`, `git add`, `git push` at the shell level. A deny list also blocks `git reset --hard`, `git checkout .`, `git clean`, `rm -rf`, and `sudo`.
- **Auto-allowed tools**: Read-only git commands, file utilities, Node/Bun/npm commands, MCP tools, Agent, Edit, Write, Task tools -- so Claude doesn't prompt you for routine operations.
- **Keybindings**: Ctrl+T (todos), Ctrl+O (transcript), Ctrl+B (background task)

## Usage: new project

### 1. Initialize project config

Open Claude Code in your project directory and run:

```
/j-init
```

This reads your project structure (package.json, tsconfig, eslint config, directory layout, etc.) and generates:

| File | Purpose |
|------|---------|
| `CLAUDE.local.md` | 30-50 lines of hard rules tailored to your project -- tech stack, conventions, key abstractions, common commands |
| `.claude/rules/*.md` | Path-scoped rule files that only load when editing matching files (e.g., migration rules load only when touching `supabase/`) |
| `.claude/settings.local.json` | PostToolUse hook for automatic type-checking after edits |
| `.gitignore` | Updated to exclude `.claude/rules/` so project config stays personal |

Start a new session after running `/j-init` to pick up the changes.

### 2. Work on your project

With the global config and project config in place, Claude Code will:
- Follow your project's conventions and hard rules automatically
- Run type-checking after edits (via the PostToolUse hook)
- Never commit, stage, or push without you explicitly asking
- Load domain-specific rules only when you're editing relevant files

### 3. Learn patterns as the project evolves

After you've made a batch of commits (or periodically), run:

```
/j-learn
```

This analyzes recent commits and extracts coding patterns into `.claude/rules/patterns.md`:
- Code that was **committed** is classified as "Prefer"
- Code that was **replaced** is classified as "Avoid"

It tracks the last analyzed commit SHA, so subsequent runs only process new commits. Capped at 15 prefer + 15 avoid entries to stay within instruction budget.

Run `/j-learn` whenever you feel Claude is drifting from your project's conventions, or after a significant refactor that establishes new patterns.

## Usage: pre-existing project

The workflow is the same. `/j-init` reads your existing codebase to generate config, so it works whether you're starting fresh or joining a mature repo.

```
cd /path/to/existing-project
# open Claude Code, then:
/j-init
```

If the project already has AI config files (`.cursorrules`, `AGENTS.md`), `/j-init` will read them and migrate relevant conventions into the Claude Code format.

After initialization, run `/j-learn` to extract patterns from your existing commit history (it analyzes the last 20 commits by default).

## Usage: after a major architecture change

If your project undergoes a fundamental change (new framework, different ORM, restructured directories, etc.), re-run `/j-init`. It's idempotent -- on subsequent runs it:

- Re-scans the project and compares against existing config
- Updates stale sections in `CLAUDE.local.md` while preserving manual additions
- Adds rules for new areas, removes rules whose paths no longer exist, updates stale rules
- Leaves `.claude/rules/patterns.md` alone (managed by `/j-learn`)
- Reports what changed rather than what was created

## Usage: new machine

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

Then open any project and run `/j-init`. Your global config (settings, hooks, keybindings) is restored immediately. Project-specific config needs to be regenerated per-project.

## Agents

Four custom agents ship with this config. They work at three levels:

1. **Automatic** -- CLAUDE.md tells Claude to spawn review/debug agents at natural checkpoints (e.g., after implementing a multi-file change). No user action needed.
2. **Explicit command** -- `/j-review` runs code-reviewer + lint-checker in parallel on your current changes.
3. **Targeted** -- `@agent-name` invokes a specific agent directly.

| Agent | Model | Purpose | Tools |
|-------|-------|---------|-------|
| `code-reviewer` | Opus | Bugs, security, performance, architecture | Read, Grep, Glob, Bash (read-only git) |
| `lint-checker` | Haiku | Style, naming, convention compliance | Read, Grep, Glob |
| `test-writer` | Sonnet | Writes tests with edge cases and failure modes | Read, Grep, Glob, Write, Bash |
| `debugger` | Opus | Structured diagnosis: hypothesis, evidence, root cause | Read, Grep, Glob, Bash |

Agents read `CLAUDE.local.md` and `.claude/rules/` first for project context, so `/j-init` should be run before using agents in a new project.

### Usage examples

```
@code-reviewer review the auth module
@test-writer write tests for src/utils/parser.ts
@debugger the API returns 500 on POST /users with valid payload
/j-review
```

### Test-first development

Ask Claude to implement a feature and it will offer test-first: `@test-writer` creates failing tests from a spec, then the main agent implements code to pass them. Works in a single session.

### Switching agent models

Use `/j-am` to switch all agents between default models and max (all Opus):

```
/j-am max       # Switch all agents to Opus
/j-am normal    # Restore default models
/j-am           # Show current model assignments
```

### Git safety in agents

Agents with Bash/Write access ship with a `<git-commit-policy>` block that prevents autonomous commits. For third-party agents installed separately, run `/j-block-agent-commits` to patch them.

## Additional commands

**`/j-block-agent-commits`** -- Claude Code hooks don't propagate to subagents spawned via the Task tool. This command patches `~/.claude/agents/*.md` files with a `<git-commit-policy>` block that prevents subagents from running git commit/add/push. Run it after installing third-party agents.

## Design philosophy

Based on research comparing Claude Code and OpenCode workflows:

- **Instruction adherence is the constraint, not context tokens.** Claude reliably follows ~150-200 instructions; the system prompt uses ~50. Config files stay concise to maximise compliance.
- **Path-scoped rules are free until triggered.** Domain-specific conventions go in `.claude/rules/` instead of a single large instruction file.
- **Hooks are deterministic but not free.** PostToolUse output accumulates in context. Only typecheck is hooked -- lint is handled by pre-commit, tests are run explicitly.
- **If Claude can discover it by reading existing files, don't write an instruction for it.** Instructions are reserved for things that cause real breakage if violated.

## License

Personal configuration. Not licensed for redistribution.
