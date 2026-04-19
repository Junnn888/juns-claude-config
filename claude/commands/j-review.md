Run a parallel code review on current changes (staged + unstaged).

## Steps

### Step 1: Check for changes

Run `git diff --stat` and `git diff --cached --stat` to identify changed files.

If there are no changes (both commands produce empty output), fall back to the last commit:

1. Run `git log -1 --format="%h %s"` to get the latest commit.
2. Use `git diff HEAD~1..HEAD` as the diff for review.
3. Report: "No uncommitted changes found. Reviewing last commit: `<short hash> <subject>`"
4. Continue to Step 2 using this diff. Mark this as **post-commit mode**.

### Step 2: Gather context

1. Run `git diff` and `git diff --cached` to get the full diffs (or `git diff HEAD~1..HEAD` in post-commit mode).
2. Read the agent instruction files:
   - `~/.claude/agents/code-reviewer.md`
   - `~/.claude/agents/lint-checker.md`

### Step 3: Spawn review agents in parallel

Send a **single message with two Agent tool calls** (this triggers parallel execution):

**Agent 1 — Code review:**
- `subagent_type`: `"general-purpose"`
- Prompt: Paste the full content of `code-reviewer.md` as the system instructions, followed by: "Review the following changes:" and the diff output. Include the list of changed files.

**Agent 2 — Lint check:**
- `subagent_type`: `"general-purpose"`
- Prompt: Paste the full content of `lint-checker.md` as the system instructions, followed by: "Check the following files for convention issues:" and the list of changed files.

### Step 4: Present unified results

Combine both agent results into a single summary:

```
## Code Review
{code-reviewer findings, by severity}

## Convention Check
{lint-checker findings, by category}

## Verdict
{Ready to commit / N issues to address}
```

If both agents report no issues, output: "Clean -- ready to commit."
