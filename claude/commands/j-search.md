Answer a question about the codebase by running parallel exploration agents with different strategies, then synthesizing findings into a clear answer.

## Steps

### Step 1: Validate input and parse the question

If `$ARGUMENTS` is empty, ask the user what they want to know and stop.

Gather project context for the search agents:

1. Read `CLAUDE.local.md` if it exists (project rules and conventions).
2. Read `.claude/rules/patterns.md` if it exists (learned prefer/avoid patterns).
3. Run `ls` at the project root to get the directory structure.

Save all of this as **project context** -- you will pass it to each agent in Step 2.

**Parse the question** from `$ARGUMENTS` and any prior conversation context (images, diagrams, error screenshots pasted earlier in the chat). Identify:
- The core question (e.g., "how does auth work", "where is payment processing", "what calls this function")
- Key terms to search for (module names, function names, concepts, file paths)
- The scope -- is this about a specific file/function, a module/feature, or the whole system?

Save this as the **search brief**.

### Step 2: Spawn 3 exploration agents in parallel

Send a **single message with 3 Agent tool calls** (this triggers parallel execution).

Each agent's prompt must start with:
- The question: `$ARGUMENTS`
- The project context gathered in Step 1
- The search brief extracted in Step 1

Then add the agent-specific exploration brief below.

**Agent 1 -- Surface Scanner:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are answering a question about a codebase. Cast a wide net to find all relevant code.

- Grep for every key term and its variations (camelCase, snake_case, PascalCase, kebab-case).
- Search file names, directory names, exports, and imports that match.
- Check for relevant constants, enums, type definitions, and config entries.
- Look at package.json scripts, route definitions, and entry points if relevant.

Report up to 15 most relevant matches. For each match, include:
- File path and line number
- The matching code snippet (2-3 lines of context)
- Why this is relevant to the question

Rank by relevance. Format as a markdown table.
```

**Agent 2 -- Structure Mapper:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are answering a question about a codebase. Map the structure and relationships of the relevant area.

- Find the main modules, files, and directories related to the question.
- Trace how they connect: what imports what, what calls what, what depends on what.
- Identify the entry points and the flow of data/control through the relevant area.
- Note key abstractions: classes, interfaces, types, hooks, stores, services that define the area's architecture.

Report:
- A dependency/call map showing how the relevant pieces connect (use arrows: A -> B -> C)
- For each node in the map: file path, what it does, and its role in the flow
- The boundaries of the area: where it starts, where it ends, what it interfaces with
```

**Agent 3 -- Context Gatherer:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are answering a question about a codebase. Gather supporting context that helps explain the area.

- Find tests related to the area -- they often document expected behavior and edge cases.
- Find type definitions, interfaces, and schemas that define the data shapes.
- Check for README files, doc comments, or inline documentation in the relevant area.
- Run: git log --oneline -10 -- {relevant paths} to find recent changes and their intent.
- Look at configuration, environment variables, and feature flags that affect the area.

Report:
- Test files and what behaviors they verify
- Key type definitions and schemas with file paths
- Any documentation found
- Recent changes and what they suggest about the area's evolution
- Configuration that affects behavior
```

### Step 3: Synthesize the answer

Cross-reference all three agent outputs:

1. **Connect the dots**: Use the structure map from Agent 2 as the backbone, fill in details from Agent 1's matches and Agent 3's context.
2. **Answer the question directly**: Start with the answer, then support it with evidence from the agents.
3. **Highlight key files**: Which files are most important for understanding this area?
4. **Note gaps**: If the agents couldn't find something, say so -- don't guess.

### Step 4: Report

Use this exact format:

```
## Answer: {one-line answer to the question}

### How it works
{2-5 paragraphs explaining the answer, referencing specific file:line locations.
Start with the high-level flow, then drill into key details.
Use the structure map to show how pieces connect.}

### Key Files
| File | Role |
|------|------|
| path/to/file | what it does in this context |

### Flow
{entry point} -> {step 2} -> {step 3} -> {outcome}
(with file:line for each step)

### Related
- Tests: {test files that verify this behavior}
- Config: {config/env that affects this area}
- Recent changes: {notable recent commits, if relevant}
```

Adjust the format to fit the question. Not every section is needed for every question -- skip sections that don't apply. For simple questions, a shorter answer is better.
