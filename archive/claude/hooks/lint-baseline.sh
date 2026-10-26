#!/usr/bin/env bash
# SessionStart hook. Takes this worktree's lint-kit suppressions snapshot the
# first time a session opens in it, so the Stop gate has a per-worktree
# baseline to compare against rather than one generated on some other branch.
# Silent unless it actually takes a snapshot: SessionStart stdout enters the
# model's context, so it prints at most one line.
# Fails OPEN throughout — a missing kit, missing jq or a non-project directory
# all exit 0 without a word.

set -euo pipefail

KIT="$HOME/.claude/lint/kit.sh"
[ -x "$KIT" ] || exit 0

input="$(cat)"

command -v jq >/dev/null 2>&1 || exit 0
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
[ -z "$cwd" ] && cwd="$PWD"
[ -d "$cwd" ] || exit 0

# No `installed` probe: `paths` costs one process instead of two and is enough
# to decide, and `baseline` below refuses on its own when the kit has no
# dependencies yet.
# Empty when this is not a git worktree with a package.json at its root.
snapshot="$("$KIT" --cwd "$cwd" paths 2>/dev/null | sed -n 's/^snapshot=//p')"
[ -n "$snapshot" ] || exit 0
[ -f "$snapshot" ] && exit 0

"$KIT" --cwd "$cwd" baseline 2>/dev/null || true
exit 0
