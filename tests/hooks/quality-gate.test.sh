#!/usr/bin/env bash
# Each case builds a throwaway git repo under a temp dir and pipes hook JSON on
# stdin with HOME overridden, so state files and logs land in the temp tree.

set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/claude/hooks/quality-gate.sh"
HOME_DIR="$(mktemp -d)"
pass=0
fail=0

check() {
  # $1 = description, $2 = condition result (0/1)
  if [ "$2" -eq 0 ]; then
    echo "ok   - $1"; pass=$((pass + 1))
  else
    echo "FAIL - $1"; fail=$((fail + 1))
  fi
}

make_repo() {
  local dir; dir="$(mktemp -d)"
  git -C "$dir" init -q
  echo "seed" > "$dir/seed.txt"
  git -C "$dir" -c user.name=t -c user.email=t@t add seed.txt
  git -C "$dir" -c user.name=t -c user.email=t@t commit -q -m init
  echo "$dir"
}

run_hook() {
  # $1 = cwd, $2 = session id; prints stderr, returns the hook's exit code.
  # HOME lives outside the repo so state files and logs never show up as
  # untracked files in the tree the hook fingerprints.
  printf '{"cwd":"%s","session_id":"%s","stop_hook_active":false}' "$1" "$2" \
    | HOME="$HOME_DIR" bash "$HOOK" 2>&1
}

# ---- case 1: no package.json -> exit 0, no output
repo="$(make_repo)"
echo "dirty" > "$repo/dirty.txt"
out="$(run_hook "$repo" s1)"; rc=$?
check "no package.json exits 0" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
check "no package.json is silent" "$([ -z "$out" ] && echo 0 || echo 1)"

# ---- case 2: failing lint on a dirty tree -> exit 2 + message
repo="$(make_repo)"
cat > "$repo/package.json" <<'JSON'
{ "name": "t", "scripts": { "lint": "exit 1", "typecheck": "exit 0" } }
JSON
out="$(run_hook "$repo" s2)"; rc=$?
check "failing lint exits 2" "$([ $rc -eq 2 ] && echo 0 || echo 1)"
case "$out" in
  *"Quality gate: npm run lint failed"*) check "failing lint names the script" 0 ;;
  *) check "failing lint names the script" 1; echo "    got: $out" ;;
esac

# ---- case 3: passing lint -> exit 0, and a repeat run skips as unchanged
repo="$(make_repo)"
cat > "$repo/package.json" <<'JSON'
{ "name": "t", "scripts": { "lint": "exit 0", "typecheck": "exit 0" } }
JSON
out="$(run_hook "$repo" s3)"; rc=$?
check "passing lint exits 0" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
out="$(run_hook "$repo" s3)"; rc=$?
check "repeat run exits 0" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
log="$HOME_DIR/.claude/hooks/quality-gate.log"
if grep -q '"mode":"skip-unchanged"' "$log" 2>/dev/null; then
  check "repeat run logs skip-unchanged" 0
else
  check "repeat run logs skip-unchanged" 1; echo "    log: $(cat "$log" 2>/dev/null)"
fi

# ---- case 4: clean tree, no untracked files -> exit 0 without running scripts
repo="$(make_repo)"
cat > "$repo/package.json" <<'JSON'
{ "name": "t", "scripts": { "lint": "exit 1" } }
JSON
git -C "$repo" -c user.name=t -c user.email=t@t add package.json
git -C "$repo" -c user.name=t -c user.email=t@t commit -q -m checks
out="$(run_hook "$repo" s4)"; rc=$?
check "clean tree skips the failing script" "$([ $rc -eq 0 ] && echo 0 || echo 1)"

echo "quality-gate: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
