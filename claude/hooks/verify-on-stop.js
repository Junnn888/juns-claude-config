#!/usr/bin/env node

// Stop hook: runs typecheck, lint, build, and tests when Claude finishes.
// If any fail, stdout keeps Claude working to fix the issues.
// Only runs when code was actually changed (git diff).

const { exec, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');

function silent(cmd) {
  try { return execSync(cmd, { encoding: 'utf8', timeout: 5000 }); }
  catch { return ''; }
}

function cwdHash() {
  return crypto.createHash('md5').update(process.cwd()).digest('hex').slice(0, 12);
}

function diffHash(diff) {
  return crypto.createHash('md5').update(diff).digest('hex');
}

function tail(str, n = 20) {
  const lines = str.split('\n');
  return lines.slice(-n).join('\n');
}

function detectPkgManager() {
  if (fs.existsSync('bun.lock')) return 'bun';
  if (fs.existsSync('pnpm-lock.yaml')) return 'pnpm';
  if (fs.existsSync('yarn.lock')) return 'yarn';
  return 'npm';
}

function readPkgScripts() {
  try {
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    return pkg.scripts || {};
  } catch { return {}; }
}

function detectVerifiers() {
  const verifiers = [];
  const pkg = detectPkgManager();
  const scripts = readPkgScripts();
  const run = pkg === 'npm' ? 'npm run' : `${pkg} run`;

  // Node.js / TypeScript
  if (fs.existsSync('package.json')) {
    if (fs.existsSync('tsconfig.json')) {
      if (scripts.typecheck) {
        verifiers.push({ name: 'TypeCheck', cmd: `${run} typecheck 2>&1`, timeout: 15000 });
      } else {
        verifiers.push({ name: 'TypeCheck', cmd: 'npx tsc --noEmit 2>&1', timeout: 15000 });
      }
    }
    if (scripts.lint) {
      verifiers.push({ name: 'Lint', cmd: `${run} lint 2>&1`, timeout: 15000 });
    }
    if (scripts.build) {
      verifiers.push({ name: 'Build', cmd: `${run} build 2>&1`, timeout: 30000 });
    }
    if (scripts.test && !/echo\s+"?Error:?\s+no test/.test(scripts.test)) {
      verifiers.push({ name: 'Tests', cmd: `${pkg} test 2>&1`, timeout: 30000 });
    }
  }

  // Go
  if (fs.existsSync('go.mod')) {
    verifiers.push({ name: 'Go Vet', cmd: 'go vet ./... 2>&1', timeout: 15000 });
    verifiers.push({ name: 'Go Build', cmd: 'go build ./... 2>&1', timeout: 30000 });
    verifiers.push({ name: 'Go Test', cmd: 'go test ./... 2>&1', timeout: 30000 });
  }

  // Python
  if (fs.existsSync('pyproject.toml')) {
    try {
      const toml = fs.readFileSync('pyproject.toml', 'utf8');
      if (toml.includes('pytest')) {
        verifiers.push({ name: 'Pytest', cmd: 'pytest 2>&1', timeout: 30000 });
      }
    } catch {}
  }

  return verifiers;
}

function runVerifier({ name, cmd, timeout }) {
  return new Promise((resolve) => {
    const child = exec(cmd, { timeout, maxBuffer: 1024 * 1024 }, (err, stdout, stderr) => {
      const output = (stdout || '') + (stderr || '');
      if (err && err.killed) {
        resolve({ name, passed: false, output: `Timed out after ${timeout / 1000}s` });
      } else if (err) {
        resolve({ name, passed: false, output: tail(output) });
      } else {
        resolve({ name, passed: true, output: '' });
      }
    });
  });
}

(async () => {
  // 1. Check for code changes
  const diff = silent('git diff --name-only 2>/dev/null');
  const cached = silent('git diff --cached --name-only 2>/dev/null');
  const changed = [...new Set([...diff.trim().split('\n'), ...cached.trim().split('\n')].filter(Boolean))];
  if (changed.length === 0) process.exit(0);

  // 2. Loop prevention
  const fullDiff = silent('git diff 2>/dev/null') + silent('git diff --cached 2>/dev/null');
  const hash = diffHash(fullDiff);
  const stateFile = path.join(os.tmpdir(), `.claude-verify-${cwdHash()}`);
  let state = { hash: '', attempts: 0 };
  try { state = JSON.parse(fs.readFileSync(stateFile, 'utf8')); } catch {}

  if (hash === state.hash) {
    process.exit(0);
  }
  fs.writeFileSync(stateFile, JSON.stringify({ hash }));

  // 3. Detect and run verifiers
  const verifiers = detectVerifiers();
  if (verifiers.length === 0) process.exit(0);

  const results = await Promise.all(verifiers.map(runVerifier));
  const allPassed = results.every(r => r.passed);

  if (allPassed) {
    // Clean up state file on success
    try { fs.unlinkSync(stateFile); } catch {}
    process.exit(0);
  }

  // 4. Report failures
  const lines = ['Verification failed. Fix the issues below before completing:', ''];
  for (const r of results) {
    if (r.passed) {
      lines.push(`## ${r.name} (PASSED)`);
    } else {
      lines.push(`## ${r.name} (FAILED)`);
      lines.push(r.output);
    }
    lines.push('');
  }
  console.log(lines.join('\n'));
  process.exit(0);
})();
