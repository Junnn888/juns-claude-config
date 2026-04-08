Update the global Claude Code configuration files in `~/.claude/` from the latest version on GitHub. This fetches, diffs, backs up, and replaces changed files while reporting exactly what changed.

## Config manifest

These are the files managed by this config. Each entry is `repo_path -> install_path`:

- `claude/CLAUDE.md` -> `~/.claude/CLAUDE.md`
- `claude/settings.json` -> `~/.claude/settings.json`
- `claude/keybindings.json` -> `~/.claude/keybindings.json`
- `claude/hooks/block-git-commit.js` -> `~/.claude/hooks/block-git-commit.js`
- `claude/commands/j-block-agent-commits.md` -> `~/.claude/commands/j-block-agent-commits.md`
- `claude/commands/j-init.md` -> `~/.claude/commands/j-init.md`
- `claude/commands/j-learn.md` -> `~/.claude/commands/j-learn.md`
- `claude/commands/j-update.md` -> `~/.claude/commands/j-update.md`
- `claude/commands/j-review.md` -> `~/.claude/commands/j-review.md`
- `claude/commands/j-am.md` -> `~/.claude/commands/j-am.md`
- `claude/agents/code-reviewer.md` -> `~/.claude/agents/code-reviewer.md`
- `claude/agents/lint-checker.md` -> `~/.claude/agents/lint-checker.md`
- `claude/agents/test-writer.md` -> `~/.claude/agents/test-writer.md`
- `claude/agents/debugger.md` -> `~/.claude/agents/debugger.md`

Base URL: `https://raw.githubusercontent.com/Junnn888/juns-claude-config/main`

## Steps

### Step 1: Fetch latest versions from GitHub

For each file in the manifest, use WebFetch to download the raw content from:
`{BASE_URL}/{repo_path}`

Fetch all files in parallel. If any fetch fails, report the failure but continue with the rest.

### Step 2: Compare with installed versions

For each file in the manifest:

1. Read the currently installed file at the install path
2. Compare the fetched content with the installed content
3. Classify as: **changed**, **unchanged**, or **new** (installed file doesn't exist)

### Step 3: Back up and install changed files

For each file classified as **changed** or **new**:

1. If the installed file exists, copy it to `{install_path}.backup.{YYYYMMDDHHMMSS}` using Bash
2. Write the fetched content to the install path using the Write tool
3. If the file is in `hooks/`, make it executable: `chmod +x {install_path}`

Create any missing directories (`hooks/`, `commands/`) before writing.

Skip files classified as **unchanged**.

### Step 4: Report

Display a summary:

```
Global config updated from Junnn888/juns-claude-config:

  File                              Status
  ----                              ------
  CLAUDE.md                         updated (backed up)
  settings.json                     unchanged
  keybindings.json                  unchanged
  hooks/block-git-commit.js         updated (backed up)
  commands/j-init.md                unchanged
  commands/j-learn.md               unchanged
  commands/j-block-agent-commits.md unchanged
  commands/j-update.md              unchanged

{N} file(s) updated, {M} unchanged.

Start a new session to pick up the changes.
```

If all files are unchanged:

```
Global config is already up to date with Junnn888/juns-claude-config.
```

If any fetches failed:

```
Failed to fetch:
  - {repo_path}: {error reason}

{N} file(s) updated, {M} unchanged, {F} failed.
```
