#!/usr/bin/env bash
# Each case builds a throwaway git repo under a temp dir and pipes hook JSON on
# stdin with HOME overridden, so state files and logs land in the temp tree.

set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/claude/hooks"
HOOK="$HOOKS_DIR/quality-gate.sh"
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

# ---- turn-start snapshot cases
run_turn_start() {
  # $1 = cwd, $2 = session id
  printf '{"cwd":"%s","session_id":"%s"}' "$1" "$2" | HOME="$HOME_DIR" bash "$HOOKS_DIR/turn-start.sh"
}

last_mode() {
  tail -n 1 "$log" | sed -n 's/.*"mode":"\([^"]*\)".*/\1/p'
}

gate_state_file() {
  # $1 = state file name, e.g. <session>.turn-start
  echo "$HOME_DIR/.claude/hooks/quality-gate-state/$1"
}

lint_repo() {
  # $1 = lint script body; prints a dirty repo whose lint runs that body
  local repo; repo="$(make_repo)"
  printf '{ "name": "t", "scripts": { "lint": "%s" } }\n' "$1" > "$repo/package.json"
  echo "$repo"
}

# ---- case 5: turn-start writes the hash tree-fingerprint.sh prints
repo="$(lint_repo "exit 0")"
out="$(run_turn_start "$repo" t5)"; rc=$?
check "turn-start exits 0 silently" "$([ $rc -eq 0 ] && [ -z "$out" ] && echo 0 || echo 1)"
expected="$(HOME="$HOME_DIR" bash "$HOOKS_DIR/tree-fingerprint.sh" "$repo")"
check "turn-start stores the tree fingerprint" \
  "$([ -n "$expected" ] && [ "$(cat "$(gate_state_file t5.turn-start)")" = "$expected" ] && echo 0 || echo 1)"

# ---- case 6: unchanged turn with no cached failure -> skip without running lint
repo="$(lint_repo "exit 1")"
run_turn_start "$repo" t6
out="$(run_hook "$repo" t6)"; rc=$?
check "unchanged turn exits 0 despite failing lint" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
check "unchanged turn logs skip-unchanged-turn" "$([ "$(last_mode)" = "skip-unchanged-turn" ] && echo 0 || echo 1)"

# ---- case 7: unchanged turn on a tree that last failed -> cached re-block
repo="$(lint_repo "echo lint-output-marker; exit 1")"
first="$(run_hook "$repo" t7)"
run_turn_start "$repo" t7
out="$(run_hook "$repo" t7)"; rc=$?
check "unchanged failing tree re-blocks with exit 2" "$([ $rc -eq 2 ] && echo 0 || echo 1)"
check "re-block repeats the cached message" "$([ "$out" = "$first" ] && echo 0 || echo 1)"
case "$out" in
  *"lint-output-marker"*) check "re-block carries the lint output" 0 ;;
  *) check "re-block carries the lint output" 1; echo "    got: $out" ;;
esac
check "re-block logs reblock-unchanged" "$([ "$(last_mode)" = "reblock-unchanged" ] && echo 0 || echo 1)"

# ---- case 8: no turn-start snapshot -> real run
repo="$(lint_repo "exit 1")"
out="$(run_hook "$repo" t8)"; rc=$?
check "missing turn-start falls through to a real run" \
  "$([ $rc -eq 2 ] && [ "$(last_mode)" = "fail" ] && echo 0 || echo 1)"

# ---- case 9: tree changed since turn-start -> real run
repo="$(lint_repo "exit 1")"
run_turn_start "$repo" t9
echo "edit" >> "$repo/seed.txt"
out="$(run_hook "$repo" t9)"; rc=$?
check "changed tree falls through to a real run" \
  "$([ $rc -eq 2 ] && [ "$(last_mode)" = "fail" ] && echo 0 || echo 1)"

# ---- case 10: a pass clears the cached failure
repo="$(lint_repo "exit 1")"
run_hook "$repo" t10 >/dev/null
check "fail writes the cached failure" \
  "$([ -f "$(gate_state_file t10.last-fail)" ] && echo 0 || echo 1)"
printf '{ "name": "t", "scripts": { "lint": "exit 0" } }\n' > "$repo/package.json"
run_hook "$repo" t10 >/dev/null
check "pass removes the cached failure" \
  "$([ ! -f "$(gate_state_file t10.last-fail)" ] && echo 0 || echo 1)"

# ---- case 11: tree-fingerprint.sh outside a git repo -> silent exit 0
plain="$(mktemp -d)"
out="$(bash "$HOOKS_DIR/tree-fingerprint.sh" "$plain")"; rc=$?
check "fingerprint outside git is silent exit 0" "$([ $rc -eq 0 ] && [ -z "$out" ] && echo 0 || echo 1)"
out="$(run_turn_start "$plain" t11)"; rc=$?
check "turn-start outside git writes nothing" \
  "$([ $rc -eq 0 ] && [ -z "$out" ] && [ ! -f "$(gate_state_file t11.turn-start)" ] && echo 0 || echo 1)"

# ---- case 12: tree-fingerprint.sh turn-unchanged mode
turn_unchanged() {
  # $1 = cwd, $2 = session id; prints stdout, returns the script's exit code
  HOME="$HOME_DIR" bash "$HOOKS_DIR/tree-fingerprint.sh" turn-unchanged "$1" "$2"
}
repo="$(lint_repo "exit 0")"
run_turn_start "$repo" t12
out="$(turn_unchanged "$repo" t12)"; rc=$?
check "turn-unchanged exits 0 silently on a match" "$([ $rc -eq 0 ] && [ -z "$out" ] && echo 0 || echo 1)"
echo "edit" >> "$repo/seed.txt"
turn_unchanged "$repo" t12 >/dev/null; rc=$?
check "turn-unchanged exits 1 on a mismatch" "$([ $rc -eq 1 ] && echo 0 || echo 1)"
turn_unchanged "$repo" t12-missing >/dev/null; rc=$?
check "turn-unchanged exits 1 without a snapshot" "$([ $rc -eq 1 ] && echo 0 || echo 1)"
turn_unchanged "$plain" t12 >/dev/null; rc=$?
check "turn-unchanged exits 1 outside git" "$([ $rc -eq 1 ] && echo 0 || echo 1)"

# ---- case 13: a Stop run prunes state files older than the threshold
repo="$(lint_repo "exit 0")"
run_turn_start "$repo" t13
echo "stale" > "$(gate_state_file old-session)"
touch -t 202001010000 "$(gate_state_file old-session)"
echo "fresh" > "$(gate_state_file fresh-session)"
run_hook "$repo" t13 >/dev/null
check "stop run prunes an old state file" "$([ ! -f "$(gate_state_file old-session)" ] && echo 0 || echo 1)"
check "stop run keeps a fresh state file" "$([ -f "$(gate_state_file fresh-session)" ] && echo 0 || echo 1)"
check "stop run keeps the current turn-start" "$([ -f "$(gate_state_file t13.turn-start)" ] && echo 0 || echo 1)"

echo "quality-gate: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
