Switch agent models between normal defaults and max (all Opus). Takes one argument: `max`, `normal`, or no argument to show current state.

## `/j-am max` — Switch all agents to Opus

1. Read all `*.md` files in `~/.claude/agents/`.
2. For each file with a `model:` field in YAML frontmatter, save the current model to `~/.claude/agents/.model-defaults.json` as a mapping of `filename -> original_model`. If the backup file already exists, do NOT overwrite it (preserve the original defaults from the first switch).
3. Use the Edit tool to replace each `model:` field value with `opus`.
4. Report a table:

```
Agent models switched to max (Opus):

| Agent           | Previous | New  |
|-----------------|----------|------|
| code-reviewer   | opus     | opus |
| lint-checker    | haiku    | opus |
| test-writer     | sonnet   | opus |
| debugger        | opus     | opus |

Note: Extended thinking is enabled globally via settings.json.
```

## `/j-am normal` — Restore default models

1. Read `~/.claude/agents/.model-defaults.json`.
2. For each entry, read the agent file and use the Edit tool to restore the saved `model:` value.
3. Delete `~/.claude/agents/.model-defaults.json` after restoring.
4. If the backup file doesn't exist, restore first-party agents to hardcoded defaults:
   - code-reviewer: opus
   - lint-checker: haiku
   - test-writer: sonnet
   - debugger: opus
   Warn that third-party agent models couldn't be restored.
5. Report a table showing `agent | previous model | restored model`.

## `/j-am` (no argument) — Show current state

1. Read all `*.md` files in `~/.claude/agents/`.
2. Check if `~/.claude/agents/.model-defaults.json` exists.
3. Report:

```
Current agent models:

| Agent           | Model   |
|-----------------|---------|
| code-reviewer   | opus    |
| lint-checker    | haiku   |
| ...             | ...     |

Mode: normal (defaults)
```

Or if `.model-defaults.json` exists:

```
Mode: max (all Opus) — run `/j-am normal` to restore defaults
```
