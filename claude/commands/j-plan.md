Generate an implementation plan by running parallel research agents, then synthesizing findings into a structured plan.

## Steps

### Step 1: Validate input and gather project context

If `$ARGUMENTS` is empty, ask the user for a task description and stop.

Gather project context for the research agents:

1. Read `CLAUDE.local.md` if it exists (project rules and conventions).
2. Read `.claude/rules/patterns.md` if it exists (learned prefer/avoid patterns).
3. Run `ls` at the project root to get the directory structure.

Save all of this as **project context** -- you will pass it to each agent in Step 2.

### Step 2: Spawn 3 research agents in parallel

Send a **single message with 3 Agent tool calls** (this triggers parallel execution).

Each agent's prompt must start with:
- The task description: `$ARGUMENTS`
- The project context gathered in Step 1

Then add the agent-specific research brief below.

**Agent 1 -- File Scout:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
Find all files, modules, and entry points related to this task.
- Trace the code paths that would be affected by this change.
- Map the dependency chain (what imports what, what calls what).
- Identify the main entry point and the call graph.

Report up to 15 most relevant files. For each file, include:
- File path
- Brief description of what it does
- Whether it would need modification, or is reference-only

Format as a markdown table.
```

**Agent 2 -- Pattern Scout:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
Find existing implementations, utilities, and patterns that could be reused for this task.
- Search for similar functionality that already exists in the codebase.
- Find shared utilities, helpers, and abstractions.
- Check .claude/rules/ for relevant conventions and constraints.
- Identify anti-patterns to avoid.

Report:
- Reusable code with file paths and function/class names
- Applicable conventions from project rules
- Anti-patterns or approaches to avoid
```

**Agent 3 -- Constraint Scout:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
Find tests, type constraints, dependencies, and recent changes that affect this task.
- Find existing tests in the affected areas (test files, test patterns used).
- Identify type definitions, interfaces, and schemas that constrain the implementation.
- Check external dependencies and their versions.
- Run: git log --oneline -10 -- {relevant paths} to find recent changes.

Report:
- Test files and what they cover
- Type constraints and interfaces to conform to
- External dependencies involved
- Recent changes that provide context
- Potential breaking changes or risks
```

### Step 3: Synthesize into structured plan

Cross-reference all three agent outputs:

1. Connect files from Agent 1 with reusable patterns from Agent 2.
2. Use constraints from Agent 3 to validate feasibility.
3. Identify gaps -- what's needed but doesn't exist yet.
4. Order implementation steps by dependency (what must be done first).
5. Flag risks, edge cases, and open questions.

### Step 4: Output the plan

Use this exact format:

```
## Plan: {one-line task summary}

### Scope
{Small / Medium / Large} -- {N files to modify, M files to create}

### Relevant Files
| File | Role | Action |
|------|------|--------|
| path/to/file.ts | description | modify / create / reference |

### Reusable Code
- `path/to/util.ts:functionName` -- what it does and how to use it

### Implementation Steps
1. {Step with specific file:function references}
2. ...

### Tests
- Existing: {test files to update}
- New: {test files to create}

### Risks & Open Questions
- {Potential issues, edge cases, unknowns}
```

Do NOT write the plan to a file. Output it directly to the conversation so it stays in context for immediate use.
