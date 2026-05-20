#!/usr/bin/env bash
# PreToolUse hook (matcher: Write|Edit|MultiEdit).
# Blocks edits to secret / credential files. Matchers filter by tool NAME
# only, so the path is checked here (per Anthropic hooks docs).
# exit 2 = block. exit 0 = allow.

set -euo pipefail

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
else
  echo "safety-files: jq not found — path not screened. Install jq to enable enforcement." >&2
  exit 0
fi

[ -z "$path" ] && exit 0

base="$(basename "$path")"

block() {
  echo "BLOCKED (secrets): editing '$path' is the user's manual step." >&2
  echo "Do NOT retry or work around it. Ask the user to make this change themselves." >&2
  exit 2
}

case "$base" in
  .env|.env.*|*.env) block ;;
  *.pem|*.key|id_rsa|id_ed25519|id_dsa|id_ecdsa) block ;;
  credentials|.git-credentials|.npmrc|.pypirc|.netrc) block ;;
esac

case "$path" in
  *.aws/credentials|*.ssh/*|*secrets/*|*/secret/*) block ;;
esac

exit 0
