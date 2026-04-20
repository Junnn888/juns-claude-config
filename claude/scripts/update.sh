#!/usr/bin/env bash
set -euo pipefail

REPO="Junnn888/juns-claude-config"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"
CLAUDE_DIR="$HOME/.claude"
TMP_DIR="/tmp/claude-config-update"

FILES=(
  "claude/CLAUDE.md:CLAUDE.md"
  "claude/settings.json:settings.json"
  "claude/keybindings.json:keybindings.json"
  "claude/hooks/block-git-commit.js:hooks/block-git-commit.js"
  "claude/hooks/verify-on-stop.js:hooks/verify-on-stop.js"
  "claude/hooks/restrict-to-project.js:hooks/restrict-to-project.js"
  "claude/commands/j-block-agent-commits.md:commands/j-block-agent-commits.md"
  "claude/commands/j-init.md:commands/j-init.md"
  "claude/commands/j-learn.md:commands/j-learn.md"
  "claude/commands/j-update.md:commands/j-update.md"
  "claude/commands/j-review.md:commands/j-review.md"
  "claude/commands/j-am.md:commands/j-am.md"
  "claude/commands/j-plan.md:commands/j-plan.md"
  "claude/commands/j-commit-pr.md:commands/j-commit-pr.md"
  "claude/agents/code-reviewer.md:agents/code-reviewer.md"
  "claude/agents/lint-checker.md:agents/lint-checker.md"
  "claude/agents/test-writer.md:agents/test-writer.md"
  "claude/agents/debugger.md:agents/debugger.md"
  "claude/scripts/update.sh:scripts/update.sh"
)

remote_version="$(curl -fsSL "$BASE_URL/claude/VERSION" 2>/dev/null || true)"
if [ -z "$remote_version" ]; then
  echo "Update failed: could not reach GitHub"
  exit 1
fi

local_version=""
[ -f "$CLAUDE_DIR/VERSION" ] && local_version="$(cat "$CLAUDE_DIR/VERSION")"

if [ "$remote_version" = "$local_version" ]; then
  echo "Config already up to date (version $remote_version)."
  exit 0
fi

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
failed=()
for entry in "${FILES[@]}"; do
  src="${entry%%:*}"
  dest="${entry##*:}"
  mkdir -p "$TMP_DIR/$(dirname "$dest")"
  if ! curl -fsSL "$BASE_URL/$src" -o "$TMP_DIR/$dest" 2>/dev/null; then
    failed+=("$dest")
    rm -f "$TMP_DIR/$dest"
  fi
done

ts="$(date +%Y%m%d%H%M%S)"
updated=0
unchanged=0
for entry in "${FILES[@]}"; do
  dest="${entry##*:}"
  fresh="$TMP_DIR/$dest"
  target="$CLAUDE_DIR/$dest"
  [ -f "$fresh" ] || continue

  if [ -f "$target" ] && diff -q "$fresh" "$target" >/dev/null 2>&1; then
    unchanged=$((unchanged + 1))
    continue
  fi

  mkdir -p "$(dirname "$target")"
  [ -f "$target" ] && cp "$target" "$target.backup.$ts"
  cp "$fresh" "$target"
  case "$dest" in
    hooks/*|scripts/*) chmod +x "$target" ;;
  esac
  updated=$((updated + 1))
done

echo "$remote_version" > "$CLAUDE_DIR/VERSION"

summary="Config updated to version $remote_version: $updated updated, $unchanged unchanged"
if [ ${#failed[@]} -gt 0 ]; then
  summary="$summary, ${#failed[@]} failed (${failed[*]})"
fi
echo "$summary. Start a new session to pick up changes."
