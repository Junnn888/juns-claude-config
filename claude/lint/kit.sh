#!/usr/bin/env bash
# Single entry point for the local lint kit. Hooks and commands call this and
# nothing else.
#
# The whole point: rules, dependencies and baselines live under ~/.claude/lint,
# never in the repo under review. Nothing here ever writes into a project.
#
# Baselines are per worktree, not per repo: a snapshot taken on one branch made
# every earlier-diverged branch look entirely new, which is what this layout
# fixes. Repo-level settings are shared (<repo_key>/settings.json); the
# suppressions, jscpd and knip baselines are keyed by worktree too.
#
# Usage: kit.sh [--cwd <dir>] <paths|installed|baseline|check|dupes|dead> [files...]

set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECTS_DIR="$KIT_DIR/projects"
BIN="$KIT_DIR/node_modules/.bin"
ESLINT_CONFIG="$KIT_DIR/eslint.config.mjs"

target="$PWD"
if [ "${1:-}" = "--cwd" ]; then
  target="${2:-}"
  shift 2
fi
cmd="${1:-}"
if [ $# -gt 0 ]; then shift; fi

sha1() {
  printf '%s' "$1" | shasum -a 1 2>/dev/null | awk '{print $1}'
}

# --- project resolution -------------------------------------------------
# Every subcommand is a silent no-op outside a git worktree with a
# package.json at its root: the kit only knows how to lint JS/TS projects.

[ -n "$target" ] && [ -d "$target" ] || exit 0
git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

toplevel="$(git -C "$target" rev-parse --show-toplevel)"
[ -f "$toplevel/package.json" ] || exit 0

common_dir="$(git -C "$target" rev-parse --git-common-dir)"
case "$common_dir" in
  /*) ;;
  *) common_dir="$toplevel/$common_dir" ;;
esac
common_dir="$(cd "$common_dir" 2>/dev/null && pwd -P || printf '%s' "$common_dir")"

repo_key="$(sha1 "$common_dir")"
worktree_key="$(sha1 "$toplevel")"
repo_dir="$PROJECTS_DIR/$repo_key"

settings_file="$repo_dir/settings.json"
snapshot_file="$repo_dir/$worktree_key.suppressions.json"
jscpd_baseline="$repo_dir/$worktree_key.jscpd.json"
knip_baseline="$repo_dir/$worktree_key.knip.json"

project_name="$(basename "$toplevel")"

# --- settings -----------------------------------------------------------

detect_tailwind_entry() {
  local candidate
  for candidate in \
    app/globals.css src/app/globals.css src/styles/globals.css \
    styles/globals.css src/index.css src/global.css app/global.css
  do
    if [ -f "$toplevel/$candidate" ] && grep -q 'tailwindcss' "$toplevel/$candidate" 2>/dev/null; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

ensure_settings() {
  if [ -f "$settings_file" ]; then return 0; fi
  local entry
  entry="$(detect_tailwind_entry || true)"
  mkdir -p "$repo_dir"
  if [ -n "$entry" ]; then
    printf '{"name":"%s","tailwindEntry":"%s"}\n' "$project_name" "$entry" > "$settings_file"
  else
    printf '{"name":"%s","tailwindEntry":null}\n' "$project_name" > "$settings_file"
  fi
}

# --- shared helpers -----------------------------------------------------

require_installed() {
  if [ -x "$BIN/eslint" ]; then return 0; fi
  echo "lint kit: not installed. Run: cd ~/.claude/lint && npm install" >&2
  exit 1
}

have_jq() { command -v jq >/dev/null 2>&1; }

branch_name() {
  git -C "$toplevel" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached"
}

suppressed_count() {
  have_jq || { echo "?"; return 0; }
  jq '[.. | objects | .count? // empty] | add // 0' "$snapshot_file" 2>/dev/null || echo "?"
}

run_eslint() {
  # Always runs from the worktree root so relative paths in the settings file
  # (the Tailwind entry point) and in git output resolve the same way.
  # --quiet costs nothing (every kit rule is an error) and drops ESLint's
  # per-comment "this disable has no effect because of noInlineConfig"
  # warnings, which are unactionable here and would otherwise fill the gate's
  # 40-line tail.
  ( cd "$toplevel" && JUN_LINT_SETTINGS="$settings_file" "$BIN/eslint" --quiet "$@" )
}

changed_files() {
  {
    git -C "$toplevel" diff --name-only --diff-filter=ACMR HEAD 2>/dev/null || true
    git -C "$toplevel" ls-files --others --exclude-standard 2>/dev/null || true
  } | sort -u | while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      *.js|*.jsx|*.mjs|*.cjs|*.ts|*.tsx) ;;
      *) continue ;;
    esac
    if [ -f "$toplevel/$f" ]; then printf '%s\n' "$f"; fi
  done
}

# --- subcommands --------------------------------------------------------

cmd_paths() {
  printf 'repo_key=%s\n' "$repo_key"
  printf 'worktree_key=%s\n' "$worktree_key"
  printf 'settings=%s\n' "$settings_file"
  printf 'snapshot=%s\n' "$snapshot_file"
  printf 'jscpd_baseline=%s\n' "$jscpd_baseline"
  printf 'knip_baseline=%s\n' "$knip_baseline"
}

cmd_baseline() {
  require_installed
  ensure_settings
  mkdir -p "$repo_dir"
  rm -f "$snapshot_file"
  # --suppress-all exits non-zero only on violations it cannot suppress (parse
  # errors); the snapshot is still written, so the run is advisory here.
  run_eslint . \
    --config "$ESLINT_CONFIG" --no-config-lookup \
    --suppress-all --suppressions-location "$snapshot_file" \
    >/dev/null 2>&1 || true

  if [ ! -f "$snapshot_file" ]; then
    echo "lint kit: no snapshot written for $project_name (nothing to suppress or eslint failed)"
    return 0
  fi

  store_jscpd_baseline >/dev/null 2>&1 || true
  store_knip_baseline >/dev/null 2>&1 || true

  echo "lint kit: snapshot taken for $project_name@$(branch_name) ($(suppressed_count) suppressed)"
}

cmd_check() {
  require_installed
  ensure_settings

  # First run in a worktree is never a block: take the snapshot and pass.
  if [ ! -f "$snapshot_file" ]; then
    cmd_baseline
    return 0
  fi

  local files=()
  if [ $# -gt 0 ]; then
    files=("$@")
  else
    while IFS= read -r f; do
      if [ -n "$f" ]; then files+=("$f"); fi
    done < <(changed_files)
  fi
  [ ${#files[@]} -gt 0 ] || return 0

  # --pass-on-unpruned-suppressions: a snapshot entry whose violation has since
  # been fixed, or that belongs to a file outside this run, must not fail the
  # gate. The snapshot is only ever pruned by re-running `baseline`.
  run_eslint "${files[@]}" \
    --config "$ESLINT_CONFIG" --no-config-lookup \
    --suppressions-location "$snapshot_file" \
    --pass-on-unpruned-suppressions
}

# --- duplication --------------------------------------------------------

jscpd_supports_baseline() {
  "$BIN/jscpd" --help 2>&1 | grep -q -- '--fail-on-new-clones'
}

run_jscpd() {
  ( cd "$toplevel" && "$BIN/jscpd" . --config "$KIT_DIR/jscpd.json" "$@" )
}

store_jscpd_baseline() {
  mkdir -p "$repo_dir"
  run_jscpd --baseline "$jscpd_baseline" --update-baseline >/dev/null 2>&1
}

cmd_dupes() {
  require_installed
  if [ ! -x "$BIN/jscpd" ]; then
    echo "lint kit: jscpd not installed, skipping duplication check."
    return 0
  fi
  if ! jscpd_supports_baseline; then
    echo "lint kit: this jscpd build has no --fail-on-new-clones, skipping duplication check."
    return 0
  fi
  if [ ! -f "$jscpd_baseline" ]; then
    if store_jscpd_baseline; then
      echo "lint kit: jscpd baseline stored for $project_name@$(branch_name)"
    else
      echo "lint kit: jscpd could not analyse $project_name, skipping duplication check."
    fi
    return 0
  fi
  # Silent reporter: jscpd's console reporter ignores the baseline and prints
  # every clone in the project (1000+ on a real codebase), while its
  # new-clone failure line carries the count. Locations come from the manual
  # re-run below, which the caller only needs when this actually fails.
  if run_jscpd --reporters silent --baseline "$jscpd_baseline" --fail-on-new-clones 0; then
    return 0
  fi
  echo "lint kit: to see every clone, including the new ones, re-run jscpd directly:" >&2
  echo "  cd $toplevel && $BIN/jscpd . --config $KIT_DIR/jscpd.json" >&2
  return 1
}

# --- dead code ----------------------------------------------------------

run_knip_json() {
  ( cd "$toplevel" && "$BIN/knip" --config "$KIT_DIR/knip.json" --reporter json 2>/dev/null || true )
}

knip_issue_count() {
  # $1 = knip's json report. Counts individual issues, not files with issues.
  printf '%s' "$1" | jq '[.issues[]? | to_entries[] | select(.value | type == "array") | .value | length] | add // 0' 2>/dev/null
}

store_knip_baseline() {
  local report count
  report="$(run_knip_json)"
  count="$(knip_issue_count "$report")"
  [ -n "$count" ] || return 1
  mkdir -p "$repo_dir"
  printf '{"count":%s}\n' "$count" > "$knip_baseline"
  printf '%s' "$count"
}

cmd_dead() {
  require_installed
  if [ ! -x "$BIN/knip" ]; then
    echo "lint kit: knip not installed, skipping dead-code check."
    return 0
  fi
  if ! have_jq; then
    echo "lint kit: jq not found, skipping dead-code check."
    return 0
  fi

  if [ ! -f "$knip_baseline" ]; then
    local stored
    if stored="$(store_knip_baseline)"; then
      echo "lint kit: knip baseline stored for $project_name@$(branch_name) ($stored issues)"
    else
      echo "lint kit: knip could not analyse $project_name, skipping dead-code check."
    fi
    return 0
  fi

  local report count baseline
  report="$(run_knip_json)"
  count="$(knip_issue_count "$report")"
  if [ -z "$count" ]; then
    echo "lint kit: knip could not analyse $project_name, skipping dead-code check."
    return 0
  fi
  baseline="$(jq -r '.count // 0' "$knip_baseline" 2>/dev/null || echo 0)"

  if [ "$count" -le "$baseline" ]; then return 0; fi

  echo "lint kit: knip reports $count issues, above this worktree's baseline of $baseline." >&2
  printf '%s' "$report" | jq -r '
    .issues[]? as $i
    | $i | to_entries[]
    | select(.value | type == "array") | select(.value | length > 0)
    | "\($i.file): \(.key): \([.value[].name] | join(", "))"
  ' >&2
  return 1
}

case "$cmd" in
  paths)     cmd_paths ;;
  installed) require_installed ;;
  baseline)  cmd_baseline ;;
  check)     cmd_check "$@" ;;
  dupes)     cmd_dupes ;;
  dead)      cmd_dead ;;
  *)
    echo "usage: kit.sh [--cwd <dir>] <paths|installed|baseline|check|dupes|dead> [files...]" >&2
    exit 64
    ;;
esac
