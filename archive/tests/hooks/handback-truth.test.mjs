// Tests for claude/hooks/handback-truth.mjs. Each case builds a throwaway git
// repo under a temp dir and runs the hook with HOME overridden, so snapshots
// and logs land in the temp tree rather than the real ~/.claude.

import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const HOOK = path.join(
  path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'claude', 'hooks', 'handback-truth.mjs',
);

function makeRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'handback-repo-'));
  const git = (...args) => execFileSync('git', args, { cwd: dir, encoding: 'utf8' });
  git('init', '-q');
  fs.writeFileSync(path.join(dir, 'seed.ts'), 'export const seed = 1;\n');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'add', 'seed.ts');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init');
  return dir;
}

function runHook(mode, payload, home) {
  return spawnSync(process.execPath, [HOOK, mode], {
    input: JSON.stringify(payload),
    encoding: 'utf8',
    env: { ...process.env, HOME: home },
  });
}

test('stop reports changed, created and new exports, then releases', () => {
  const repo = makeRepo();
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'handback-home-'));
  const agentId = 'agent-1';

  const start = runHook('--start', { agent_id: agentId, agent_type: 'builder', cwd: repo }, home);
  assert.equal(start.status, 0);
  const stateFile = path.join(home, '.claude', 'hooks', 'handback-state', `${agentId}.json`);
  assert.ok(fs.existsSync(stateFile));

  fs.appendFileSync(path.join(repo, 'seed.ts'), 'const extra = 2;\n');
  fs.writeFileSync(path.join(repo, 'made.ts'), 'export const x = 1;\n');

  const stop = runHook('--stop', { agent_id: agentId, agent_type: 'builder', cwd: repo }, home);
  assert.equal(stop.status, 0);
  const out = JSON.parse(stop.stdout);
  assert.equal(out.decision, 'block');
  assert.match(out.reason, /Changed: seed\.ts \(\+1\/-0\)/);
  assert.match(out.reason, /Created: made\.ts \(2 lines\)/);
  assert.match(out.reason, /New exports: made\.ts: export const x = 1;/);

  const second = runHook(
    '--stop', { agent_id: agentId, agent_type: 'builder', cwd: repo, stop_hook_active: true }, home,
  );
  assert.equal(second.status, 0);
  assert.equal(second.stdout.trim(), '');
  assert.equal(fs.existsSync(stateFile), false);
});

test('read-only agent never bounces', () => {
  const repo = makeRepo();
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'handback-home-'));
  const agentId = 'agent-2';

  runHook('--start', { agent_id: agentId, agent_type: 'patch', cwd: repo }, home);
  const stop = runHook('--stop', { agent_id: agentId, agent_type: 'patch', cwd: repo }, home);
  assert.equal(stop.status, 0);
  assert.equal(stop.stdout.trim(), '');
});
