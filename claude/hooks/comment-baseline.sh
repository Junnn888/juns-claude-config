#!/usr/bin/env bash
# Baselines a repo's narration-comment rate before judging the Stop hook:
# runs comment-suspects.mjs over the added lines of the last N commits and
# prints suspects per 100 added lines. Run from inside the target repo.
# Usage: comment-baseline.sh [N]   (default 20)

set -euo pipefail

N="${1:-20}"
DETECTOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/comment-suspects.mjs"

command -v node >/dev/null 2>&1 || { echo "node not found on PATH" >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git repository" >&2; exit 1; }

total_added=0
total_suspects=0

while read -r sha; do
  # Root commits have no parent to diff against.
  git rev-parse -q --verify "$sha~1" >/dev/null 2>&1 || continue
  out="$(node "$DETECTOR" --diff-from "$sha~1..$sha")" || continue
  added="$(printf '%s\n' "$out" | awk '/^ADDED /{print $2}')"
  suspects="$(printf '%s\n' "$out" | grep -c '^SUSPECT ')" || true
  total_added=$((total_added + ${added:-0}))
  total_suspects=$((total_suspects + ${suspects:-0}))
  printf '%s  added=%-6s suspects=%s\n' "${sha:0:8}" "${added:-0}" "${suspects:-0}"
  printf '%s\n' "$out" | sed -n 's/^SUSPECT /    /p'
done < <(git log --format=%H -n "$N")

echo "----"
if [ "$total_added" -gt 0 ]; then
  rate="$(awk -v s="$total_suspects" -v a="$total_added" 'BEGIN{printf "%.1f", s*100/a}')"
else
  rate="0.0"
fi
echo "total: $total_suspects suspects / $total_added added lines = $rate per 100 added lines"
