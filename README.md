# juns-claude-config

Personal Claude Code configuration. Installs global settings, hooks, permissions, and commands to `~/.claude/`.

The purpose of this config is to be able to achieve as much of opencode's niceities as possible, while using the claude max plan. Opencode Zen and Openrouter = expenny :(

UPDATE: 10/04/2026 it's pretty awful tbh

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
  hooks/verify-on-stop.js          Runs typecheck/lint/build/tests before Claude stops
  commands/
    j-init.md                       Scaffolds project-specific config
    j-learn.md                      Extracts prefer/avoid patterns from commits
    j-review.md                     Parallel code review + lint check
    j-am.md                         Switch agent models (normal/max)
    j-plan.md                       Parallel research + structured implementation plan
    j-commit-pr.md                  Generates commit message + filled PR template from staged diff
    j-search.md                     Parallel codebase exploration to answer questions about the code
    j-debug.md                      Parallel search to triangulate where a bug/error originates
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
- **Verification on stop**: A Stop hook automatically runs available typecheckers, linters, build scripts, and tests when Claude finishes implementation work. If anything fails, Claude sees the output and continues fixing. Only runs when code was actually changed.
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

### 4. Plan before you build

Before starting a non-trivial task, run:

```
/j-plan add OAuth2 authentication to the API layer
```

This spawns 3 parallel research agents (Haiku) that simultaneously investigate:
- **File Scout** -- relevant files, entry points, and dependency chains
- **Pattern Scout** -- reusable code, existing patterns, and conventions
- **Constraint Scout** -- tests, type constraints, dependencies, and recent changes

Results are synthesized into a structured plan with scope, files, implementation steps, tests, and risks. The research runs on Haiku for speed and cost; the synthesis runs on your current model.

### 5. Ask questions about the codebase

When you want to understand how something works, run:

```
/j-search how does authentication work in this project
```

This spawns 3 parallel exploration agents:
- **Surface Scanner** -- greps for relevant terms, files, exports, and definitions
- **Structure Mapper** -- traces module relationships, call graphs, and data flow
- **Context Gatherer** -- finds tests, types, docs, config, and recent changes

Results are synthesized into a direct answer with key files, execution flow, and supporting context. It also reads conversation context, so you can paste a screenshot or diagram before running the command.

### 6. Debug with parallel search

When you need to find where a bug or error originates, run:

```
/j-debug where does the 400 response come from on POST /api/users
```

This spawns 3 parallel search agents that attack the problem from different angles:
- **Surface Scanner** -- greps for error messages, status codes, route paths, and their variations
- **Code Path Tracer** -- traces the execution path from entry point through the call chain
- **Guard & Config Inspector** -- finds validators, auth guards, middleware, and config that could produce the symptom

Results are triangulated: locations that appear across multiple agents are flagged as high-confidence matches.

### 7. Generate commit messages and PR descriptions

When you have staged changes ready, run:

```
/j-commit-pr
```

This reads `git diff --cached`, searches for a PR template in `.github/`, and generates:
- A commit message matching your project's recent commit style
- A filled-out PR template with all markdown preserved

"Type of Change" checkboxes are auto-checked based on diff analysis. Testing checkboxes are left unchecked for manual verification. Output is in code blocks for easy copy-paste.

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

1. **Automatic** -- The global Stop hook handles mechanical verification (typecheck, lint, build, tests). CLAUDE.md suggests spawning review/debug agents at natural checkpoints (e.g., after implementing a multi-file change).
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
- **Hooks are deterministic but not free.** PostToolUse typecheck runs per-edit (project-local). The global Stop hook runs typecheck/lint/build/tests once at completion -- right tradeoff between feedback speed and context cost.
- **If Claude can discover it by reading existing files, don't write an instruction for it.** Instructions are reserved for things that cause real breakage if violated.

## License

Personal configuration. Not licensed for redistribution.
