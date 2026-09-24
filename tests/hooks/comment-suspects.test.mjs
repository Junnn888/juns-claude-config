// Tests for the turn-start skip in claude/hooks/comment-suspects.mjs. Each case
// builds a throwaway git repo and runs the hook with HOME overridden, so state
// files and logs land in the temp tree rather than the real ~/.claude.

import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const HOOKS_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'claude', 'hooks');

function makeRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'comment-repo-'));
  const git = (...args) => execFileSync('git', args, { cwd: dir, encoding: 'utf8' });
  git('init', '-q');
  fs.writeFileSync(path.join(dir, 'seed.ts'), 'export const seed = 1;\n');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'add', 'seed.ts');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init');
  // A narration comment the Stop hook would bounce on if it scanned the tree.
  fs.appendFileSync(path.join(dir, 'seed.ts'), '// First we loop over the users\nconst users = [];\n');
  return dir;
}

function runStop(payload, home) {
  return spawnSync(process.execPath, [path.join(HOOKS_DIR, 'comment-suspects.mjs')], {
    input: JSON.stringify(payload), encoding: 'utf8', env: { ...process.env, HOME: home },
  });
}

function snapshotTurnStart(payload, home) {
  execFileSync('bash', [path.join(HOOKS_DIR, 'turn-start.sh')], {
    input: JSON.stringify(payload), env: { ...process.env, HOME: home },
  });
}

const lastLog = (home) => {
  const lines = fs.readFileSync(path.join(home, '.claude', 'hooks', 'comment-bounce.log'), 'utf8').trim().split('\n');
  return JSON.parse(lines[lines.length - 1]);
};

test('turn that left the tree unchanged logs no-tree-change and never scans', () => {
  const repo = makeRepo();
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'comment-home-'));
  const payload = { cwd: repo, session_id: 'turn-1', stop_hook_active: false };

  snapshotTurnStart(payload, home);
  const stop = runStop(payload, home);
  assert.equal(stop.status, 0);
  assert.equal(stop.stdout.trim(), '');
  assert.equal(lastLog(home).mode, 'no-tree-change');
});

test('turn that changed the tree still scans and bounces', () => {
  const repo = makeRepo();
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'comment-home-'));
  const payload = { cwd: repo, session_id: 'turn-2', stop_hook_active: false };

  snapshotTurnStart(payload, home);
  fs.appendFileSync(path.join(repo, 'seed.ts'), 'const more = 2;\n');
  const stop = runStop(payload, home);
  assert.equal(stop.status, 0);
  assert.equal(JSON.parse(stop.stdout).decision, 'block');
  assert.equal(lastLog(home).mode, 'bounce');
});

test('missing turn-start falls through to the existing checks', () => {
  const repo = makeRepo();
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'comment-home-'));
  const stop = runStop({ cwd: repo, session_id: 'turn-3', stop_hook_active: false }, home);
  assert.equal(JSON.parse(stop.stdout).decision, 'block');
});
