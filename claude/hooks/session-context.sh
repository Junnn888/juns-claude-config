#!/usr/bin/env bash
# SessionStart hook. stdout becomes context Claude can see (per Anthropic
# docs). Keep it MINIMAL and high-signal — bloat here taxes every session.
# Silent + exit 0 if not a git repo.

set -euo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

branch="$(git branch --show-current 2>/dev/null || echo 'detached')"
dirty_count="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

if [ "$dirty_count" -eq 0 ]; then
  state="clean"
else
  state="$dirty_count uncommitted change(s)"
fi

echo "## Repo context"
echo "Branch: $branch ($state)"
echo "Recent commits:"
git log --oneline -5 2>/dev/null || true

exit 0
