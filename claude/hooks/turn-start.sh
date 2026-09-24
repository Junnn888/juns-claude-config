#!/usr/bin/env bash
# UserPromptSubmit hook. Snapshots the tree fingerprint at turn start so the
# Stop hooks can skip turns that changed nothing. Silent, and always exits 0:
# a failure here only means the Stop hooks fall back to their full checks.

source "$(dirname "${BASH_SOURCE[0]}")/tree-fingerprint.sh" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)" || exit 0
session_id="$(printf '%s' "$input" | jq -r '.session_id // "unknown"' 2>/dev/null)" || exit 0
[ -z "$cwd" ] && cwd="$PWD"

git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
fingerprint="$(tree_fingerprint "$cwd")" || exit 0
[ -n "$fingerprint" ] || exit 0

mkdir -p "$GATE_STATE_DIR" 2>/dev/null \
  && printf '%s' "$fingerprint" > "$(session_state_file "$session_id").turn-start" 2>/dev/null
exit 0
