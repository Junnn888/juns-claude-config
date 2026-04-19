#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const TARGETED = new Set(['cat', 'ls', 'find']);

function main() {
  let input;
  try {
    input = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'));
  } catch {
    process.exit(0);
  }

  const command = (input.tool_input?.command || '').trim();
  if (!command) process.exit(0);

  const projectDir = process.cwd();
  const subCommands = command.split(/\s*(?:&&|\|\||[;|])\s*/);
  let hasTargeted = false;
  const outsidePaths = [];

  for (const sub of subCommands) {
    const trimmed = sub.trim();
    if (!trimmed) continue;

    const baseCmd = extractBaseCommand(trimmed);
    if (!TARGETED.has(baseCmd)) continue;

    hasTargeted = true;
    const paths = extractPaths(baseCmd, trimmed);

    for (const p of paths) {
      const resolved = resolvePath(p, projectDir);
      if (resolved === null || !isInside(resolved, projectDir)) {
        outsidePaths.push(p);
      }
    }
  }

  if (!hasTargeted) process.exit(0);

  if (outsidePaths.length > 0) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        permissionDecision: 'ask',
        reason: `Path outside project directory: ${outsidePaths[0]}`
      }
    }));
  } else {
    console.log(JSON.stringify({
      hookSpecificOutput: { permissionDecision: 'allow' }
    }));
  }
  process.exit(0);
}

function extractBaseCommand(subcmd) {
  const tokens = subcmd.split(/\s+/);
  for (const token of tokens) {
    if (/^\w+=/.test(token)) continue;
    return path.basename(token);
  }
  return '';
}

function extractPaths(cmd, subcmd) {
  const allTokens = subcmd.split(/\s+/);
  let i = 0;
  while (i < allTokens.length && /^\w+=/.test(allTokens[i])) i++;
  i++;
  const args = allTokens.slice(i);

  if (cmd === 'find') return extractFindPaths(args);
  return extractGeneralPaths(args);
}

function extractGeneralPaths(args) {
  const paths = [];
  for (const a of args) {
    if (a === '<<' || a.startsWith('<<')) return [];
    if (a === '-' || a.startsWith('-')) continue;
    if (a.startsWith('>') || a === '2>&1') continue;
    paths.push(a);
  }
  return paths;
}

function extractFindPaths(args) {
  const paths = [];
  for (const a of args) {
    if (a.startsWith('-') || a === '(' || a === ')' || a === '!' || a === ',') break;
    paths.push(a);
  }
  return paths;
}

function resolvePath(p, projectDir) {
  if (p === '~') p = os.homedir();
  else if (p.startsWith('~/')) p = path.join(os.homedir(), p.slice(2));
  if (p.includes('$')) return null;
  return path.resolve(projectDir, p);
}

function isInside(resolved, projectDir) {
  return resolved === projectDir || resolved.startsWith(projectDir + path.sep);
}

main();
