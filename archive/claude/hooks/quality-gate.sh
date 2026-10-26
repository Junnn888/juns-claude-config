#!/usr/bin/env bash
# Stop hook. Blocks the turn from ending while the project's lint or typecheck
# fails, or while the local lint kit finds violations above this worktree's
# snapshot. Silent in projects with neither.
# The kit (~/.claude/lint) carries its own rules and dependencies, so projects
# that own no lint scripts — and projects the user does not own — still get
# size, complexity and duplication enforcement without a single file written
# into the repo.
# Mechanic: exit 2 = block + stderr fed back to Claude. exit 0 = allow.
# Claude Code overrides after 8 consecutive blocks, which is the runaway guard —
# so this hook deliberately does NOT early-exit on stop_hook_active: the gate
# must re-check after every fix attempt.
# Design: documented exception to the repo's <200ms hook target. Stop fires once
# per turn, and the checks only run when the tree changed since the last pass
# (per-session tree fingerprint), so pure Q&A turns never pay for tsc. A turn
# that changed nothing since its UserPromptSubmit snapshot (turn-start.sh) is
# skipped too, or re-blocked from the cached failure if that tree last failed.

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/tree-fingerprint.sh"
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

find "$GATE_STATE_DIR" -type f -mmin +"$GATE_STATE_MAX_AGE_MIN" -delete 2>/dev/null || true

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

KIT="$HOME/.claude/lint/kit.sh"
kit_available=0
if [ -x "$KIT" ] && "$KIT" --cwd "$cwd" installed >/dev/null 2>&1; then
  kit_available=1
fi

scripts=()
has_script lint && scripts+=("lint")
has_script typecheck && scripts+=("typecheck")
if [ ${#scripts[@]} -eq 0 ] && [ "$kit_available" -eq 0 ]; then
  log "skip-no-checks" ""
  exit 0
fi

# Nothing uncommitted and nothing untracked: there is nothing this turn could
# have broken that a previous gate did not already see.
if [ -z "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]; then
  log "skip-unchanged" ""
  exit 0
fi

state_file="$(session_state_file "$session_id")"
fail_file="$state_file.last-fail"
fingerprint="$(tree_fingerprint "$cwd")"

if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "$fingerprint" ]; then
  log "skip-unchanged" ""
  exit 0
fi

if turn_unchanged "$cwd" "$session_id" "$fingerprint"; then
  if [ -f "$fail_file" ] && [ "$(head -n 1 "$fail_file")" = "$fingerprint" ]; then
    tail -n +2 "$fail_file" >&2
    log "reblock-unchanged" ""
    exit 2
  fi
  log "skip-unchanged-turn" ""
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
report=""

record_failure() {
  # $1 = headline, $2 = command output (last 40 lines kept)
  failed=1
  report+="$1"$'\n'"$(printf '%s\n' "$2" | tail -n 40)"$'\n'
}

if [ ${#scripts[@]} -gt 0 ]; then
  for script in "${scripts[@]}"; do
    ran="${ran:+$ran,}$script"
    out="$( (cd "$cwd" && $manager run ${silent:+$silent} "$script") 2>&1 )" && continue
    record_failure "Quality gate: $manager run $script failed. Fix the root cause; do not disable rules, add suppressions, or delete tests to pass." "$out"
  done
fi

if [ "$kit_available" -eq 1 ]; then
  ran="${ran:+$ran,}kit"
  if ! out="$("$KIT" --cwd "$cwd" check 2>&1)"; then
    record_failure "Quality gate: lint kit found violations above this worktree's snapshot. Fix the code; do not add disables or suppressions." "$out"
  fi
fi

if [ "$failed" -eq 1 ]; then
  printf '%s' "$report" >&2
  mkdir -p "$GATE_STATE_DIR" 2>/dev/null \
    && { printf '%s\n' "$fingerprint"; printf '%s' "$report"; } > "$fail_file" 2>/dev/null || true
  log "fail" "$ran"
  exit 2
fi

mkdir -p "$GATE_STATE_DIR" 2>/dev/null && printf '%s' "$fingerprint" > "$state_file" 2>/dev/null || true
rm -f "$fail_file"
log "pass" "$ran"
exit 0
