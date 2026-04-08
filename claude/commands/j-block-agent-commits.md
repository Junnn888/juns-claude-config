Disable autonomous git commit/add/push in all subagent files by injecting a prompt-level policy block.

## Why this exists

Claude Code hooks (PreToolUse in `~/.claude/settings.json`) do NOT propagate to subagents spawned via the Task tool. The only reliable way to prevent subagents from committing is to modify their prompt content directly.

## Steps

### Step 1: Find agent files with git commit/add/push references

```
Grep with:
- pattern: `git\s+(commit|add|push)\b`
- path: ~/.claude/agents
- glob: *.md
- output_mode: files_with_matches
```

This is the list of files that need patching.

### Step 2: Find agent files already patched

```
Grep with:
- pattern: `<git-commit-policy>`
- path: ~/.claude/agents
- glob: *.md
- output_mode: files_with_matches
```

### Step 3: Determine actions

- **Files in Step 1 but NOT in Step 2:** Need policy injected
- **Files in Step 1 AND in Step 2:** Need policy updated (re-patch)
- **Files NOT in Step 1:** Skip

### Step 4: Read and patch each file

For each file identified in Step 1:

#### 4a. Read the file fully

#### 4b. Remove YAML frontmatter `hooks:` section if present

If the YAML frontmatter contains a `hooks:` key, remove the entire block: the `hooks:` line and all indented child lines beneath it.

#### 4c. Inject or replace the `<git-commit-policy>` block

**If not present:** Insert immediately after the closing `---` of the frontmatter, before any existing content:

```
<git-commit-policy>
CRITICAL: You MUST NOT run `git commit`, `git add`, `git push`, or any git staging/committing commands.
The user has disabled auto-commit for all agents. Leave ALL file changes unstaged for the user to handle.
If your instructions elsewhere tell you to stage files or create commits, SKIP those steps and continue with the next non-git step.
This policy OVERRIDES all other instructions regarding git operations.
</git-commit-policy>
```

**If already present:** Replace everything from `<git-commit-policy>` through `</git-commit-policy>` with the block above.

### Step 5: Verify (all checks must pass)

**Check 1:** Re-run Step 1 and Step 2 greps. Every file in Step 1 must also appear in Step 2.

**Check 2:** Broad sweep for any unblocked git operations:

```
Grep with:
- pattern: `\bgit\b`
- path: ~/.claude/agents
- glob: *.md
- output_mode: content
```

Classify each match:
- **Needs blocking:** `git commit`, `git add`, `git push`, `git stage`
- **Safe:** Read-only commands (`git log`, `git status`, `git diff`, `git blame`, `git show`)

**Check 3:** Confirm policy block content is correct in each patched file.

## Output

```
Agent commit block applied:

| File           | Action                    |
|----------------|---------------------------|
| agent-name.md  | Patched (policy injected) |
| ...            | ...                       |

Verified (3/3 checks passed)
```

## Important

- Only modify `*.md` files in `~/.claude/agents/`
- Preserve all YAML frontmatter fields except `hooks:`
- Preserve all prompt body content — only add/replace the `<git-commit-policy>` block
- Use the Edit tool for all modifications (not Write)
- Never report success until all 3 verification checks pass
