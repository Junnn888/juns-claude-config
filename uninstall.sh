#!/usr/bin/env bash
# Uninstalls Jun's Claude Code config.
# Usage:  curl -fsSL <raw-url>/uninstall.sh | bash
#
# If a backup from install.sh exists, restores the newest one.
# Otherwise removes only the files this config installs.

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
TS="$(date +%Y%m%d-%H%M%S)"
MARKETPLACE_NAME="juns-config"
LSP_PLUGIN="jun-lsp"

# Remove the self-authored LSP plugin + marketplace first (guarded).
# Removing the marketplace also uninstalls plugins from it, but we do both
# explicitly for clarity.
if command -v claude >/dev/null 2>&1; then
  echo "==> Removing LSP plugin + marketplace"
  claude plugin uninstall "${LSP_PLUGIN}@${MARKETPLACE_NAME}" --scope user 2>/dev/null || true
  claude plugin marketplace remove "$MARKETPLACE_NAME" 2>/dev/null || true
else
  echo "==> 'claude' not on PATH — remove the LSP plugin manually if needed:"
  echo "      claude plugin marketplace remove $MARKETPLACE_NAME"
fi

newest_backup="$(ls -d "$CLAUDE_DIR".backup.* 2>/dev/null | sort | tail -n1 || true)"

if [ -n "$newest_backup" ] && [ -d "$newest_backup" ]; then
  echo "==> Found backup: $newest_backup"
  if [ -d "$CLAUDE_DIR" ]; then
    cp -a "$CLAUDE_DIR" "$CLAUDE_DIR.pre-uninstall.$TS"
    echo "==> Current config saved to $CLAUDE_DIR.pre-uninstall.$TS"
    rm -rf "$CLAUDE_DIR"
  fi
  cp -a "$newest_backup" "$CLAUDE_DIR"
  echo "==> Restored ~/.claude from backup."
else
  echo "==> No backup found. Removing installed files only."
  rm -f "$CLAUDE_DIR/CLAUDE.md" \
        "$CLAUDE_DIR/settings.json" \
        "$CLAUDE_DIR/hooks/safety-bash.sh" \
        "$CLAUDE_DIR/hooks/safety-files.sh" \
        "$CLAUDE_DIR/hooks/session-context.sh"
  echo "==> Removed. LEARNINGS.md (if present) was left in place on purpose."
  echo "    Note: a fresh ~/.claude/settings.json was NOT recreated — Claude"
  echo "    Code will fall back to defaults. Re-add any settings you need."
fi

echo "Done. Start a new Claude Code session for changes to take effect."
