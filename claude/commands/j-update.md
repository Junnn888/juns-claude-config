Update the global Claude Code configuration files in `~/.claude/` from the latest version on GitHub.

Uses a VERSION file to skip unnecessary work — only fetches all files when the version has changed.

## Config manifest

These are the files managed by this config. Each entry is `repo_path -> install_path`:

- `claude/VERSION` -> `~/.claude/VERSION`
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
- `claude/commands/j-plan.md` -> `~/.claude/commands/j-plan.md`
- `claude/commands/j-commit-pr.md` -> `~/.claude/commands/j-commit-pr.md`
- `claude/agents/code-reviewer.md` -> `~/.claude/agents/code-reviewer.md`
- `claude/agents/lint-checker.md` -> `~/.claude/agents/lint-checker.md`
- `claude/agents/test-writer.md` -> `~/.claude/agents/test-writer.md`
- `claude/agents/debugger.md` -> `~/.claude/agents/debugger.md`

Base URL: `https://raw.githubusercontent.com/Junnn888/juns-claude-config/main`

## Steps

### Step 1: Version check

1. Run `curl -sf {BASE_URL}/claude/VERSION` via Bash to fetch the remote version (a single integer on one line).
2. Read `~/.claude/VERSION` if it exists.
3. Compare:
   - **If both exist and match**: print `Global config is already up to date (version {N}).` and **stop** — do not proceed to further steps.
   - **If they differ, or local VERSION does not exist**: continue to Step 2.

If the remote fetch fails, warn the user and **stop**: `Failed to fetch version from GitHub. Check your network connection.`

### Step 2: Download all files

Run a single Bash command that uses `curl` to download every file in the manifest to `/tmp/claude-config-update/`, preserving directory structure (`hooks/`, `commands/`, `agents/`). Create subdirectories first with `mkdir -p`.

Use the format:
```bash
mkdir -p /tmp/claude-config-update/{hooks,commands,agents} && \
BASE="https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/claude" && \
curl -sf "$BASE/VERSION" -o /tmp/claude-config-update/VERSION && \
curl -sf "$BASE/CLAUDE.md" -o /tmp/claude-config-update/CLAUDE.md && \
# ... etc for all files
```

If any individual file fails to download, note it but continue with the rest.

### Step 3: Compare and install

For each file in the manifest (except VERSION):

1. Compare `/tmp/claude-config-update/{file}` with the installed version at `~/.claude/{file}` using `diff -q`
2. Classify as: **changed**, **unchanged**, or **new** (installed file doesn't exist)

For each file classified as **changed** or **new**:

1. If the installed file exists, back it up: `cp {install_path} {install_path}.backup.{YYYYMMDDHHMMSS}`
2. Write the fetched content to the install path using the Write tool
3. If the file is in `hooks/`, make it executable: `chmod +x {install_path}`

Create any missing directories before writing.

Skip files classified as **unchanged**.

### Step 4: Write version and report

1. Write the remote VERSION content to `~/.claude/VERSION` using the Write tool.
2. Display a summary:

```
Global config updated to version {N} from Junnn888/juns-claude-config:

  File                              Status
  ----                              ------
  CLAUDE.md                         updated (backed up)
  settings.json                     unchanged
  keybindings.json                  unchanged
  hooks/block-git-commit.js         updated (backed up)
  commands/j-init.md                unchanged
  ...

{X} file(s) updated, {Y} unchanged.

Start a new session to pick up the changes.
```

If any downloads failed:

```
Failed to download:
  - {file}: {error reason}

{X} file(s) updated, {Y} unchanged, {F} failed.
```
