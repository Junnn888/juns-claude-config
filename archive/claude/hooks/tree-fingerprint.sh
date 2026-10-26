#!/usr/bin/env bash
# Tree fingerprint shared by the Stop gate and the UserPromptSubmit turn-start
# snapshot: sha1 of `git diff HEAD` plus one line per untracked file (path,
# size, mtime). Also the one owner of the session-to-state-file rule.
# Executed:
#   tree-fingerprint.sh [dir]
#       prints the hash for dir (default $PWD), or nothing outside a git work
#       tree; always exits 0.
#   tree-fingerprint.sh turn-unchanged <dir> <session_id>
#       exits 0 only when the session's turn-start snapshot exists and matches
#       the current tree; 1 otherwise. No stdout.
# Sourced: defines the functions and GATE_STATE_DIR without running anything.

GATE_STATE_DIR="$HOME/.claude/hooks/quality-gate-state"
# Mirrors STATE_MAX_AGE_MS (7 days) in comment-suspects.mjs.
GATE_STATE_MAX_AGE_MIN=10080

file_stamp() {
  stat -f '%z %m' "$1" 2>/dev/null || stat -c '%s %Y' "$1" 2>/dev/null || echo "? ?"
}

tree_fingerprint() {
  local dir="$1"
  {
    git -C "$dir" diff HEAD 2>/dev/null || git -C "$dir" diff 2>/dev/null || true
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      printf '%s %s\n' "$f" "$(file_stamp "$dir/$f")"
    done < <(git -C "$dir" ls-files --others --exclude-standard 2>/dev/null || true)
  } | shasum -a 1 2>/dev/null | awk '{print $1}'
}

session_state_file() {
  printf '%s/%s' "$GATE_STATE_DIR" "$(printf '%s' "$1" | tr -c '[:alnum:]_-' '_')"
}

turn_unchanged() {
  # $1 = dir, $2 = session id, $3 = current fingerprint (computed when omitted)
  local turn_start
  turn_start="$(session_state_file "$2").turn-start"
  [ -f "$turn_start" ] && [ "$(cat "$turn_start")" = "${3:-$(tree_fingerprint "$1")}" ]
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  if [ "${1:-}" = "turn-unchanged" ]; then
    [ -n "${2:-}" ] && [ -n "${3:-}" ] || exit 1
    git -C "$2" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 1
    turn_unchanged "$2" "$3" && exit 0
    exit 1
  fi
  dir="${1:-$PWD}"
  git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
  tree_fingerprint "$dir" || true
  exit 0
fi
