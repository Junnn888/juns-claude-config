Diagnose where a bug, error, or unexpected behavior originates by running parallel search agents with different strategies, then triangulating the most likely root cause.

## Steps

### Step 1: Validate input and extract search signals

If `$ARGUMENTS` is empty, ask the user what they're looking for and stop.

Gather project context for the search agents:

1. Read `CLAUDE.local.md` if it exists (project rules and conventions).
2. Read `.claude/rules/patterns.md` if it exists (learned prefer/avoid patterns).
3. Run `ls` at the project root to get the directory structure.

Save all of this as **project context** -- you will pass it to each agent in Step 2.

**Extract search signals** from `$ARGUMENTS` and any prior conversation context (images, error messages, stack traces pasted earlier in the chat). Identify and list:
- Error messages or status codes (e.g., "400", "Unauthorized", "ENOENT")
- Route paths or URLs (e.g., "/api/users", "POST /auth/login")
- Function, class, or variable names
- File paths mentioned
- Behavioral descriptions (e.g., "check is failing", "redirect loop", "returns null")

Expand each signal into search term variations where applicable (e.g., status code "400" -> also "BadRequest", "bad_request", "BAD_REQUEST", "HTTP_400").

Save this as the **signal list**.

### Step 2: Spawn 3 search agents in parallel

Send a **single message with 3 Agent tool calls** (this triggers parallel execution).

Each agent's prompt must start with:
- The search description: `$ARGUMENTS`
- The project context gathered in Step 1
- The signal list extracted in Step 1

Then add the agent-specific search brief below.

**Agent 1 -- Surface Scanner:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are searching for where something is in a codebase. Use the signal list to cast a wide net.

- Grep for every signal and its variations. Try multiple phrasings.
- Check error/exception definitions, HTTP response builders, validation schemas.
- Search string literals, constants, and enum values that match the signals.
- Look at error message templates and i18n/translation files if they exist.

Report up to 15 most relevant matches. For each match, include:
- File path and line number
- The matching code snippet (2-3 lines of context)
- Why this match is relevant to the search

Rank by relevance: direct matches > indirect matches > tangential matches.
Format as a markdown table.
```

**Agent 2 -- Code Path Tracer:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are tracing the code path that produces the observed behavior.

- Find the entry point: route definition, handler, controller, or event listener that matches the signals.
- Trace the execution path forward through the call chain: route -> middleware -> handler -> service -> validation -> response.
- At each step, note what checks, transformations, or branches exist.
- Identify where the behavior (error, response, side effect) is produced.

Report the call chain as an ordered list:
1. {file:line} -- {what happens here}
2. {file:line} -- {what happens here}
...

If you find multiple possible paths, report each as a separate chain.
```

**Agent 3 -- Guard & Config Inspector:**
- `subagent_type`: `"Explore"` (thoroughness: `"very thorough"`)
- Prompt:

```
You are looking for checks, guards, and configuration that could produce the observed behavior.

- Search for auth guards, validators, rate limiters, permission checks, feature flags, schema validators.
- Check middleware registration order and which middleware runs on the relevant routes.
- Look at configuration files, environment variables, and feature toggles that affect the behavior.
- Check error handling layers: error transformers, error middleware, catch blocks that wrap or remap errors.

Report potential causes. For each:
- File path and line number
- What condition the check enforces
- What happens when the check fails (what error/response is produced)
- How confident you are this is related (High / Medium / Low)

Format as a markdown list grouped by confidence level.
```

### Step 3: Triangulate

Cross-reference all three agent outputs:

1. **High-confidence matches**: Files or functions that appear in 2+ agent reports.
2. **Execution path**: Combine the tracer's call chain with surface matches to build the full picture.
3. **Root cause candidate**: Identify the specific check, guard, or code location most likely producing the observed behavior.
4. **Conflicts**: Flag any contradictions between agent findings.

### Step 4: Report

Use this exact format:

```
## Debug: {one-line description of what was found}

### Most Likely Location
`{file:line}` -- {description of what this code does and why it matches the search}

### Execution Path
`{entry point}` -> `{middleware}` -> `{handler}` -> **`{failing check}`** -> `{error response}`
(with file:line for each step, bold the most relevant node)

### Other Matches
| File | Line | Relevance | Why |
|------|------|-----------|-----|
| path/to/file | 42 | High/Med/Low | brief reason |

### Search Coverage
- Surface Scanner: {N files matched, top search terms used}
- Code Path Tracer: {traced from X entry point through Y steps}
- Guard Inspector: {N checks/guards found in the area}
```

If no clear location is found, report what was searched and ruled out so the user doesn't retrace those steps. Suggest what to look at next.
