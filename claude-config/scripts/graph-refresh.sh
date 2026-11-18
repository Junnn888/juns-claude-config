#!/usr/bin/env bash
# Rebuilds the code graph of the git project that holds the given folder,
# from a snapshot of its default branch. Usage: graph-refresh.sh [--force] [dir]
set -euo pipefail

force=0
dir="$PWD"
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    *) dir="$arg" ;;
  esac
done

die() { echo "graph-refresh: $*" >&2; exit 2; }

command -v graphify >/dev/null || die "graphify is not installed (uv tool install --python 3.13 graphifyy)"

main_checkout=$(git -C "$dir" worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p' || true)
[ -n "$main_checkout" ] || die "$dir is not inside a git project"

# Same naming rule as /jun-setup, so the graph sits beside <project>-instructions.md.
project=$(basename "$main_checkout" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')
[ -n "$project" ] || die "cannot derive a project name from $main_checkout"

default_ref=$(git -C "$main_checkout" symbolic-ref --quiet --short refs/remotes/origin/HEAD || true)
if [ -z "$default_ref" ]; then
  for candidate in origin/main origin/master main master; do
    if git -C "$main_checkout" rev-parse --verify --quiet "$candidate^{commit}" >/dev/null; then
      default_ref="$candidate"
      break
    fi
  done
fi
[ -n "$default_ref" ] || die "cannot tell the default branch of $project"

fetch_note=""
if [ "${default_ref#origin/}" != "$default_ref" ]; then
  git -C "$main_checkout" fetch --quiet origin "${default_ref#origin/}" \
    || fetch_note=" (fetch failed, used the last fetched copy)"
fi
commit=$(git -C "$main_checkout" rev-parse "$default_ref^{commit}")

source_dir="$HOME/graphify-sources/$project"
out_dir="$HOME/graphify-graphs/$project"
graph="$out_dir/graph.json"
stamp="$out_dir/.source_commit"
run_log="$out_dir/refresh-last.log"
history_log="$HOME/graphify-graphs/refresh.log"

if [ "$force" -eq 0 ] && [ -f "$graph" ] && [ "$(cat "$stamp" 2>/dev/null)" = "$commit" ]; then
  echo "$project: graph is already at $default_ref ${commit:0:8}$fetch_note"
  exit 0
fi

started=$(date +%s)
rm -rf "$source_dir"
mkdir -p "$source_dir" "$out_dir"
git -C "$main_checkout" archive "$commit" | tar -x -C "$source_dir"

export GRAPHIFY_OUT="$out_dir" GRAPHIFY_NO_TIPS=1 GRAPHIFY_NO_BACKUP=1

# A fresh graph and manifest, so files deleted on the default branch drop out.
rm -f "$graph" "$out_dir/manifest.json"

: > "$run_log"
if ! GRAPHIFY_BACKEND=none graphify extract "$source_dir" --code-only >>"$run_log" 2>&1; then
  tail -15 "$run_log" >&2
  die "extract failed for $project (full output: $run_log)"
fi

naming="named"
if ! command -v claude >/dev/null \
  || ! GRAPHIFY_BACKEND=claude-cli GRAPHIFY_CLAUDE_CLI_MODEL="${GRAPHIFY_CLAUDE_CLI_MODEL:-sonnet}" \
       graphify cluster-only "$source_dir" >>"$run_log" 2>&1; then
  naming="unnamed"
  if ! GRAPHIFY_BACKEND=none graphify cluster-only "$source_dir" --no-label >>"$run_log" 2>&1; then
    tail -15 "$run_log" >&2
    die "grouping failed for $project (full output: $run_log)"
  fi
fi

graphify export callflow-html --graph "$graph" --output "$out_dir/callflow.html" >>"$run_log" 2>&1 || true

[ -f "$graph" ] || die "no graph was written for $project (full output: $run_log)"
echo "$commit" > "$stamp"

instructions="$HOME/.claude/$project-instructions.md"
instructions_note="no $instructions yet: run /jun-setup in the main checkout so sessions use the graph"
if [ -f "$instructions" ]; then
  instructions_note="sessions already told about the graph"
  if ! grep -q "graphify-graphs/$project/graph.json" "$instructions"; then
    cat >> "$instructions" <<EOF

A code graph of this repo's default branch is at
~/graphify-graphs/$project/graph.json. To find code you have not
been pointed to, query the graph before searching:
\`graphify query "<names>" --graph ~/graphify-graphs/$project/graph.json --budget 4000\`,
\`graphify explain "<name>" --graph ~/graphify-graphs/$project/graph.json\` and
\`graphify affected "<name>" --graph ~/graphify-graphs/$project/graph.json\`.
Query by concrete names such as a file path or a function name, because
matching is by keyword. Open each file the graph points to before relying on
it, and search normally for code that exists only on a branch, because the
graph does not have it.
EOF
    instructions_note="added the graph paragraph to $instructions"
  fi
fi

nodes=$(sed -n 's/.*graph\.json: \([0-9]*\) nodes.*/\1/p' "$run_log" | tail -1)
elapsed=$(( $(date +%s) - started ))
summary="$project: rebuilt from $default_ref ${commit:0:8}$fetch_note, ${nodes:-?} nodes, groups $naming, ${elapsed}s"
echo "$(date '+%Y-%m-%d %H:%M') $summary" >> "$history_log"
echo "$summary"
echo "$instructions_note"
