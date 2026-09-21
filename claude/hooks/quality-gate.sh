#!/usr/bin/env bash
# Stop hook. Blocks the turn from ending while the project's lint or typecheck
# fails. Silent in projects without those scripts.
# Mechanic: exit 2 = block + stderr fed back to Claude. exit 0 = allow.
# Claude Code overrides after 8 consecutive blocks, which is the runaway guard —
# so this hook deliberately does NOT early-exit on stop_hook_active: the gate
# must re-check after every fix attempt.
# Design: documented exception to the repo's <200ms hook target. Stop fires once
# per turn, and the checks only run when the tree changed since the last pass
# (per-session tree fingerprint), so pure Q&A turns never pay for tsc.

set -euo pipefail

STATE_DIR="$HOME/.claude/hooks/quality-gate-state"
LOG_FILE="$HOME/.claude/hooks/quality-gate.log"

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
  session_id="$(printf '%s' "$input" | jq -r '.session_id // "unknown"')"
  stop_hook_active="$(printf '%s' "$input" | jq -r '.stop_hook_active // false')"
else
  # jq missing: cannot parse the hook payload. Fail OPEN so the session stays
  # usable, and warn. Install jq for this hook to enforce.
  echo "quality-gate: jq not found — lint/typecheck not run. Install jq to enable enforcement." >&2
  exit 0
fi

[ -z "$cwd" ] && cwd="$PWD"
[ -d "$cwd" ] || exit 0

start_s="$(date +%s)"

log() {
  # $1 = mode, $2 = scripts run (comma-separated, may be empty)
  local dur=$(( ($(date +%s) - start_s) * 1000 ))
  mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || return 0
  printf '{"ts":"%s","cwd":"%s","mode":"%s","scripts":"%s","duration_ms":%s,"stop_hook_active":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$cwd" "$1" "$2" "$dur" "$stop_hook_active" \
    >> "$LOG_FILE" 2>/dev/null || true
}

git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
[ -f "$cwd/package.json" ] || exit 0

has_script() {
  jq -e --arg s "$1" '.scripts[$s] // empty' "$cwd/package.json" >/dev/null 2>&1
}

scripts=()
has_script lint && scripts+=("lint")
has_script typecheck && scripts+=("typecheck")
if [ ${#scripts[@]} -eq 0 ]; then
  log "skip-no-checks" ""
  exit 0
fi

# Nothing uncommitted and nothing untracked: there is nothing this turn could
# have broken that a previous gate did not already see.
if [ -z "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]; then
  log "skip-unchanged" ""
  exit 0
fi

file_stamp() {
  stat -f '%z %m' "$1" 2>/dev/null || stat -c '%s %Y' "$1" 2>/dev/null || echo "? ?"
}

tree_fingerprint() {
  {
    git -C "$cwd" diff HEAD 2>/dev/null || git -C "$cwd" diff 2>/dev/null || true
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      printf '%s %s\n' "$f" "$(file_stamp "$cwd/$f")"
    done < <(git -C "$cwd" ls-files --others --exclude-standard 2>/dev/null || true)
  } | shasum -a 1 2>/dev/null | awk '{print $1}'
}

state_file="$STATE_DIR/$(printf '%s' "$session_id" | tr -c '[:alnum:]_-' '_')"
fingerprint="$(tree_fingerprint)"

if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "$fingerprint" ]; then
  log "skip-unchanged" ""
  exit 0
fi

if [ -f "$cwd/bun.lock" ] || [ -f "$cwd/bun.lockb" ]; then
  manager="bun"; silent="--silent"
elif [ -f "$cwd/pnpm-lock.yaml" ]; then
  manager="pnpm"; silent="--silent"
elif [ -f "$cwd/yarn.lock" ]; then
  manager="yarn"; silent=""
else
  manager="npm"; silent="--silent"
fi

failed=0
ran=""
for script in "${scripts[@]}"; do
  ran="${ran:+$ran,}$script"
  out="$( (cd "$cwd" && $manager run ${silent:+$silent} "$script") 2>&1 )" && continue
  failed=1
  echo "Quality gate: $manager run $script failed. Fix the root cause; do not disable rules, add suppressions, or delete tests to pass." >&2
  printf '%s\n' "$out" | tail -n 40 >&2
done

if [ "$failed" -eq 1 ]; then
  log "fail" "$ran"
  exit 2
fi

mkdir -p "$STATE_DIR" 2>/dev/null && printf '%s' "$fingerprint" > "$state_file" 2>/dev/null || true
log "pass" "$ran"
exit 0
