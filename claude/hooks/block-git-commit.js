#!/usr/bin/env node

// Blocks autonomous git commit/add commands from Claude agents.
// To allow Claude to commit, remove the PreToolUse hook from ~/.claude/settings.json

const input = JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'));
const command = input.tool_input?.command || '';

// Match git at command boundaries: start of string or after shell operators (&&, ||, ;, |)
if (/(^|[;&|]\s*)git\s+(commit|add)\b/.test(command)) {
  console.log(
    'BLOCKED: git commit/add is not allowed. The user has disabled auto-commit. ' +
    'Do NOT attempt to commit or stage changes. Leave all changes unstaged for the user to handle.'
  );
  process.exit(2);
}

process.exit(0);
