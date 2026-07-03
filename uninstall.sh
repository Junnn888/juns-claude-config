#!/usr/bin/env bash
# Uninstalls Jun's Claude Code config.
# Usage:  curl -fsSL <raw-url>/uninstall.sh | bash
#
# If a backup from install.sh exists, restores the newest one.
# Otherwise removes only the files this config installs.

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
TS="$(date +%Y%m%d-%H%M%S)"

# Official LSP plugins (claude-plugins-official) installed by install.sh are
# left in place — they're shared first-party Anthropic infrastructure you may
# rely on across projects. Remove any manually if you want, e.g.:
#   claude plugin uninstall ruby-lsp@claude-plugins-official --scope user

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
        "$CLAUDE_DIR/statusLine.sh" \
        "$CLAUDE_DIR/hooks/safety-bash.sh" \
        "$CLAUDE_DIR/hooks/safety-files.sh" \
        "$CLAUDE_DIR/hooks/session-context.sh"
  echo "==> Removed. LEARNINGS.md and mcp.json (if present) were left in place"
  echo "    on purpose — they may hold your own lessons / extra MCP servers."
  echo "    Note: a fresh ~/.claude/settings.json was NOT recreated — Claude"
  echo "    Code will fall back to defaults. Re-add any settings you need."
fi

echo "Done. Start a new Claude Code session for changes to take effect."
