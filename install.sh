#!/usr/bin/env bash
set -euo pipefail

# Claude Code configuration installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash

REPO="Junnn888/juns-claude-config"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"
CLAUDE_DIR="$HOME/.claude"

# Files to install
FILES=(
  "claude/VERSION:VERSION"
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

echo "Installing Claude Code config from $REPO..."
echo ""

# Create directories
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/commands"
mkdir -p "$CLAUDE_DIR/agents"
mkdir -p "$CLAUDE_DIR/scripts"

# Backup existing files
backup_if_exists() {
  local file="$1"
  if [ -f "$file" ]; then
    local backup="${file}.backup.$(date +%Y%m%d%H%M%S)"
    cp "$file" "$backup"
    echo "  Backed up: $(basename "$file") -> $(basename "$backup")"
  fi
}

# Install each file
for entry in "${FILES[@]}"; do
  src="${entry%%:*}"
  dest="${entry##*:}"
  target="$CLAUDE_DIR/$dest"

  backup_if_exists "$target"

  if curl -fsSL "$BASE_URL/$src" -o "$target" 2>/dev/null; then
    echo "  Installed: $dest"
  else
    echo "  FAILED:    $dest (check repo access)"
  fi
done

# Make hook executable
chmod +x "$CLAUDE_DIR/hooks/block-git-commit.js" 2>/dev/null || true
chmod +x "$CLAUDE_DIR/hooks/verify-on-stop.js" 2>/dev/null || true
chmod +x "$CLAUDE_DIR/hooks/restrict-to-project.js" 2>/dev/null || true
chmod +x "$CLAUDE_DIR/scripts/update.sh" 2>/dev/null || true

echo ""
echo "Done. Config installed to $CLAUDE_DIR/"
echo ""
echo "Next steps:"
echo "  1. Open any project directory"
echo "  2. Run: claude"
echo "  3. Type: /j-init"
echo "     This scaffolds project-specific config (CLAUDE.local.md, .claude/rules/, typecheck hook)"
echo ""
echo "To update later, re-run this script."
