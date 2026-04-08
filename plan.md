# Claude Code Agents & Subagents — Planning Brief

> **Purpose:** This document summarises research and discussion on how to best utilise agents and subagents within Claude Code. It is intended as input for a planning agent to implement these patterns into our project configuration. Treat this as a starting point for discussion — challenge assumptions, propose alternatives, and adapt to our specific codebase needs.

---

## How subagents work (the key concepts)

Claude Code's main agent runs a single-threaded loop. When it delegates work, it spawns a **subagent** — a fresh, isolated Claude instance with its own 200K-token context window. The subagent does its work independently and only its **final summary** returns to the parent. All intermediate steps (file reads, tool calls, reasoning) stay inside the subagent and are discarded. This is the core mechanism for keeping the main context clean during long sessions.

Subagents are invoked via the **Agent tool** (formerly called Task). Three built-in subagents ship with Claude Code: **Explore** (Haiku, read-only, for codebase discovery), **Plan** (read-only, for research before proposing), and **general-purpose** (full tool access). Custom subagents are defined as Markdown files with YAML frontmatter.

**Critical constraint:** subagents cannot spawn other subagents. The architecture is strictly one level deep — hub-and-spoke. For deeper orchestration, chain tasks through the main conversation or use Agent Teams (experimental).

---

## Model selection strategy

### The "use Opus for everything" argument

Boris Cherny (Claude Code's creator) uses Opus for all tasks. His reasoning: even though Opus is slower per-token, it requires less steering and gets things right more often, making it faster end-to-end. He ships 20–30 PRs per day with this approach.

### The tiered approach (recommended starting point)

For cost-conscious usage that still prioritises quality where it matters:

| Model | Use for | Rationale |
|---|---|---|
| **Opus** | Code review (bug-finding, security), complex debugging, architectural decisions, multi-module refactors | Correctness matters most here; a missed bug costs more than the token difference |
| **Sonnet** | Default main agent, standard implementation, feature work, test writing | Best balance of speed, quality, and cost for daily work |
| **Haiku** | Exploration subagents (file search, grep, codebase discovery), lint/style checks, simple refactors | ~80% cheaper than Sonnet; perfectly capable for read-only and pattern-matching tasks |

**Discussion point for planning agent:** Should we start with the tiered approach and graduate to Opus-for-everything if the steering overhead proves costly? Or commit to Opus from the start given our codebase complexity? Consider trialling both for a week and comparing output quality and cost.

---

## Agents to create

The following custom subagents are recommended. Each should be a `.md` file stored in `.claude/agents/` (project-level, committed to git) or `~/.claude/agents/` (user-level, all projects).

### 1. `code-reviewer`

- **Model:** opus
- **Tools:** Read, Grep, Glob, Bash (read-only commands)
- **Permission mode:** plan
- **Purpose:** Reviews code changes for bugs, logic errors, security issues, and architectural concerns. Should rank findings by severity with specific line references and suggested fixes.
- **When to use:** After any meaningful code change, before committing.

### 2. `lint-checker`

- **Model:** haiku
- **Tools:** Read, Grep, Glob
- **Permission mode:** plan
- **Purpose:** Checks for style consistency, naming conventions, CLAUDE.md compliance, and code formatting issues. Lightweight complement to the code-reviewer.
- **When to use:** Automatically via hooks on write/edit, or before PR.

### 3. `test-writer`

- **Model:** sonnet
- **Tools:** Read, Grep, Glob, Bash, Write
- **Permission mode:** default
- **Purpose:** Writes comprehensive tests for a given module or function. Should aim for edge cases and failure modes, not just happy paths.
- **When to use:** Before implementation (test-first pattern) or after implementation to fill coverage gaps.

### 4. `debugger`

- **Model:** opus
- **Tools:** Read, Grep, Glob, Bash
- **Permission mode:** default
- **Purpose:** Structured debugging: capture error → reproduce → isolate → fix → verify. Should state its hypothesis before investigating.
- **When to use:** When a bug has multiple possible causes or spans multiple modules.

### 5. `explorer`

- **Model:** haiku
- **Tools:** Read, Grep, Glob
- **Permission mode:** plan
- **Purpose:** Codebase discovery and research. Answers questions like "where is X implemented?", "what depends on Y?", "how does Z flow through the system?" without polluting main context.
- **When to use:** Before any implementation to understand the current state of the code.

**Discussion point for planning agent:** Are there project-specific agents we should add (e.g. a Node.js/dependency auditor, a documentation writer)? Should any of these be user-level (`~/.claude/agents/`) rather than project-level?

---

## How to invoke agents

Three methods, in order of flexibility:

1. **Natural language** — "Use the code-reviewer subagent to check the auth module." The main agent decides whether to invoke.
2. **@-mention** — `@code-reviewer analyse the changes in src/api/`. Guarantees the subagent runs.
3. **Session-wide** — `claude --agent code-reviewer` to start an entire session as that agent persona.

For automation, @-mention is preferred as it's deterministic.

---

## Running agents in parallel

Parallelism is where the largest speed gains come from. A 10-minute sequential investigation becomes ~30 seconds with parallel subagents.

### How to trigger it

Be **explicit** in your prompts. Claude won't reliably parallelise unless told to:

- **Good:** "Use 4 parallel tasks: one to explore the auth module, one to explore the API routes, one to check test coverage, one to review error handling."
- **Bad:** "Look into the codebase and find any issues." (runs sequentially)

Specify what each subagent should focus on and set **file scope boundaries** to prevent overlap (e.g. "Agent 1: only files in `src/auth/`. Agent 2: only files in `src/api/`.").

### Sweet spot

2–4 focused parallel agents for most tasks. More than 4–5 rarely helps due to diminishing returns and rate limit pressure. Each subagent has ~2–3 seconds of startup latency.

### The context multiplier

Three parallel subagents give ~600K tokens of working memory without polluting the main conversation. The main agent receives only concise summaries.

### Agent Teams (experimental alternative)

For truly independent parallel work (e.g. competing debugging hypotheses), Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) allows 2–16 Claude Code instances to coordinate via a shared task list with direct inter-agent messaging. This is heavier-weight than subagents and consumes 3–7× more tokens. Use selectively.

---

## Configuration recommendations

### Recommended `settings.json` baseline

```json
{
  "model": "sonnet",
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku"
  }
}
```

### Hooks to implement

- **PostToolUse on Write|Edit** — auto-format code after every edit (100% style compliance vs ~80% from CLAUDE.md)
- **PreToolUse on Bash(git commit)** — block commits unless tests pass (forces test-and-fix loop)
- **Stop hook** — trigger code-reviewer subagent when Claude finishes working

### CLAUDE.md principles

- Keep under ~150 total instructions (beyond this, every low-value rule dilutes high-value ones)
- Treat every Claude mistake as a new rule
- Don't specify code style rules — use linters/formatters via hooks instead
- Focus on guardrails for what Claude gets wrong, not a comprehensive manual

### Context hygiene

- Use `/clear` between distinct tasks
- Compact at logical breakpoints with `/compact`
- Monitor with `/context` — sessions above ~70% utilisation produce noticeably worse code
- Auto-compaction triggers at ~95% but quality has already degraded by then

---

## Recommended workflow pattern

1. **Plan** — Start in Plan Mode (Shift+Tab). Have Claude interview you about edge cases. Save spec to `SPEC.md`.
2. **Explore** — Use `@explorer` to understand relevant parts of the codebase before touching anything.
3. **Test first** — Session A uses `@test-writer` to write tests. Session B implements code to pass them.
4. **Implement** — Use parallel subagents for independent domains (e.g. frontend agent + backend agent + database agent in separate file scopes).
5. **Review** — `@code-reviewer` for bugs/security, `@lint-checker` for style. Run in parallel.
6. **Debug** — `@debugger` for complex issues. Agent Teams for competing hypotheses.
7. **Clear and repeat** — `/clear` between tasks. Every mistake becomes a CLAUDE.md rule.

---

## Open questions for the planning agent

1. Which agents should be project-level vs user-level?
2. Should we trial Opus-for-everything vs the tiered approach for a week and compare?
3. Are there project-specific hooks we need beyond the three recommended?
4. What's the right `maxTurns` for each agent given our codebase size?
5. Should we set up git worktrees for parallel session isolation?
6. Do we want a documentation-writer agent or a dependency-auditor agent?
