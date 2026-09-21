#!/usr/bin/env node
// SubagentStart + SubagentStop hook (matcher: builder|patch). Snapshots the git
// tree when a writer agent starts, diffs it when the agent stops, and bounces
// the stop once with a facts block the agent could not have invented — so the
// orchestrator can check its `Reused:` / `Wrote new:` claims without re-reading
// files.
// Mechanic: a SubagentStop block is delivered to the SUBAGENT, not the parent,
// so the agent is told to fold the facts into its own report. Bounce-once via
// stop_hook_active, as in comment-suspects.mjs.
//
// Modes:
//   --start   SubagentStart — writes the snapshot, prunes old ones.
//   --stop    SubagentStop — diffs, blocks once, then releases.
//
// Known limitation: a second writer active in the same tree during the agent's
// run is attributed to this agent. The orchestrator style now forbids parallel
// writers for that reason.
//
// Hook modes must never brick a session: any internal error exits 0.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const STATE_DIR = path.join(os.homedir(), '.claude', 'hooks', 'handback-state');
const LOG_FILE = path.join(os.homedir(), '.claude', 'hooks', 'handback.log');
const STATE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const CODE_EXTS = new Set(['js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs']);
const MAX_EXPORTS = 20;
const EXPORT_LINE_MAX = 100;

// ---------------------------------------------------------------- git

function git(cwd, args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
}

const inGitRepo = (cwd) => {
  try { git(cwd, ['rev-parse', '--is-inside-work-tree']); return true; }
  catch { return false; }
};

function countLines(cwd, file) {
  try {
    const text = fs.readFileSync(path.join(cwd, file), 'utf8');
    return text === '' ? 0 : text.split('\n').length;
  } catch { return 0; }
}

function snapshot(cwd) {
  const tracked = {};
  let numstat = '';
  try { numstat = git(cwd, ['diff', 'HEAD', '--numstat']); } catch { /* no HEAD yet */ }
  for (const line of numstat.split('\n')) {
    if (!line.trim()) continue;
    const [added, deleted, file] = line.split('\t');
    if (!file) continue;
    tracked[file] = { added: Number(added) || 0, deleted: Number(deleted) || 0 };
  }

  const untracked = {};
  let others = '';
  try { others = git(cwd, ['ls-files', '--others', '--exclude-standard']); } catch { /* ignore */ }
  for (const file of others.split('\n')) {
    if (!file.trim()) continue;
    untracked[file] = countLines(cwd, file);
  }

  return { ts: new Date().toISOString(), cwd, tracked, untracked };
}

// Export lines present now but not in the HEAD version of the file. An
// untracked file has no HEAD version, so every export line counts as new.
function newExports(cwd, file) {
  const ext = path.extname(file).slice(1).toLowerCase();
  if (!CODE_EXTS.has(ext)) return [];
  let head = '';
  try { head = git(cwd, ['show', `HEAD:${file}`]); } catch { /* new file */ }
  const before = new Set(head.split('\n').filter((l) => /^export\s/.test(l)).map((l) => l.trim()));
  let current = '';
  try { current = fs.readFileSync(path.join(cwd, file), 'utf8'); } catch { return []; }
  return current
    .split('\n')
    .filter((l) => /^export\s/.test(l))
    .map((l) => l.trim())
    .filter((l) => !before.has(l))
    .map((l) => (l.length > EXPORT_LINE_MAX ? l.slice(0, EXPORT_LINE_MAX) : l));
}

// ---------------------------------------------------------------- state + log

const stateFile = (agentId) =>
  path.join(STATE_DIR, `${String(agentId).replace(/[^\w-]/g, '_')}.json`);

function saveState(agentId, data) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    fs.writeFileSync(stateFile(agentId), JSON.stringify(data));
  } catch { /* state is best-effort */ }
}

function loadState(agentId) {
  try { return JSON.parse(fs.readFileSync(stateFile(agentId), 'utf8')); }
  catch { return null; }
}

function dropState(agentId) {
  try { fs.unlinkSync(stateFile(agentId)); } catch { /* already gone */ }
}

function pruneState() {
  try {
    const cutoff = Date.now() - STATE_MAX_AGE_MS;
    for (const f of fs.readdirSync(STATE_DIR)) {
      const full = path.join(STATE_DIR, f);
      try { if (fs.statSync(full).mtimeMs < cutoff) fs.unlinkSync(full); } catch { /* ignore */ }
    }
  } catch { /* no state dir yet */ }
}

function log(entry) {
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
    fs.appendFileSync(LOG_FILE, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + '\n');
  } catch { /* logging must never block */ }
}

// ---------------------------------------------------------------- diff

function derive(cwd, before, now) {
  const changed = [];
  for (const [file, stats] of Object.entries(now.tracked)) {
    const prev = before.tracked[file] || { added: 0, deleted: 0 };
    const added = stats.added - prev.added;
    const deleted = stats.deleted - prev.deleted;
    if (added !== 0 || deleted !== 0) changed.push({ file, added, deleted });
  }
  const created = [];
  for (const [file, lines] of Object.entries(now.untracked)) {
    if (!(file in before.untracked)) created.push({ file, lines });
    else if (before.untracked[file] !== lines) changed.push({ file, added: lines - before.untracked[file], deleted: 0 });
  }

  const exports = [];
  for (const { file } of [...changed, ...created]) {
    for (const line of newExports(cwd, file)) {
      if (exports.length >= MAX_EXPORTS) break;
      exports.push({ file, line });
    }
    if (exports.length >= MAX_EXPORTS) break;
  }

  return { changed, created, exports };
}

function buildReason({ changed, created, exports }) {
  const lines = [
    'Ground truth from git since this agent started (computed by a hook, not from memory):',
    `Changed: ${changed.map((c) => `${c.file} (+${c.added}/-${c.deleted})`).join(', ')}`,
    `Created: ${created.map((c) => `${c.file} (${c.lines} lines)`).join(', ')}`,
  ];
  if (exports.length) {
    lines.push(`New exports: ${exports.map((e) => `${e.file}: ${e.line}`).join('; ')}`);
  }
  lines.push(
    '',
    'Check your report\'s file list and its `Reused:` / `Wrote new:` line against this. ' +
    'Correct any mismatch — a file under Created that your report calls a reuse is a mismatch. ' +
    'Then append the three lines above verbatim under the heading `Ground truth (git)` at the ' +
    'end of your report, and finish.',
  );
  return lines.join('\n');
}

// ---------------------------------------------------------------- modes

function runStart(input) {
  const cwd = input.cwd || process.cwd();
  const agentId = input.agent_id || 'unknown';
  pruneState();
  if (!inGitRepo(cwd)) { log({ agent_id: agentId, agent_type: input.agent_type, mode: 'no-git' }); return; }
  saveState(agentId, snapshot(cwd));
  log({ agent_id: agentId, agent_type: input.agent_type, mode: 'snapshot' });
}

function runStop(input) {
  const cwd = input.cwd || process.cwd();
  const agentId = input.agent_id || 'unknown';
  const base = { agent_id: agentId, agent_type: input.agent_type };

  // Bounce once: the agent has already been handed the facts this stop.
  if (input.stop_hook_active) {
    dropState(agentId);
    log({ ...base, mode: 'released' });
    return;
  }

  const before = loadState(agentId);
  if (!before) { log({ ...base, mode: 'no-snapshot' }); return; }
  if (!inGitRepo(cwd)) { dropState(agentId); log({ ...base, mode: 'no-git' }); return; }

  const { changed, created, exports } = derive(cwd, before, snapshot(cwd));
  if (changed.length === 0 && created.length === 0) {
    dropState(agentId);
    log({ ...base, mode: 'no-changes' });
    return;
  }

  const reason = buildReason({ changed, created, exports });
  process.stdout.write(JSON.stringify({ decision: 'block', reason }) + '\n');
  log({ ...base, mode: 'bounce', changed: changed.length, created: created.length, exports: exports.length });
}

// ---------------------------------------------------------------- entry

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    const timer = setTimeout(() => resolve(null), 5000);
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => {
      clearTimeout(timer);
      try { resolve(JSON.parse(data)); } catch { resolve(null); }
    });
    process.stdin.on('error', () => { clearTimeout(timer); resolve(null); });
  });
}

async function main() {
  const argv = process.argv.slice(2);
  const input = await readStdin();
  if (!input || typeof input !== 'object') return;
  if (argv.includes('--start')) runStart(input);
  else if (argv.includes('--stop')) runStop(input);
}

main().then(() => process.exit(0)).catch((err) => {
  // A broken hook must not brick every dispatch.
  log({ mode: 'error', error: String(err && err.message || err) });
  process.exit(0);
});
