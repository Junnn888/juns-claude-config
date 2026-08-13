#!/usr/bin/env node
// Stop hook: nominates comment lines added this turn and blocks the stop once
// per turn so the model can act on each. Two suspect kinds carry different
// instructions: narration ("First we loop over the users") gets delete-or-keep;
// long doc blocks above exports get compress-to-the-load-bearing-lines. The
// script only nominates — content judgment stays with the model.
//
// Modes:
//   (default)            Stop hook — reads hook JSON on stdin.
//   --baseline-session   SessionStart hook — pre-seeds the session's state
//                        with suspects already in the dirty tree, so leftovers
//                        from previous sessions are never bounced on.
//   --diff-from <rev>    CLI — prints ADDED/SUSPECT lines for `git diff <rev>`
//                        (accepts an A..B range; used by comment-baseline.sh).
//
// Hook modes must never brick a session: any internal error exits 0.

import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const STATE_DIR = path.join(os.homedir(), '.claude', 'hooks', 'comment-bounce-state');
const LOG_FILE = path.join(os.homedir(), '.claude', 'hooks', 'comment-bounce.log');
const MAX_ADDED_LINES = 2000;
const STATE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const MUTATING_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash']);

const NARRATION_REASON =
  'Comment-cleanup pass: the added comment lines below look like generation ' +
  'narration rather than rationale. For each, either DELETE it (it restates ' +
  'what the code already says) or KEEP it (it carries something the code ' +
  'cannot express — rationale, invariant, gotcha).';

const DOC_BLOCK_REASON =
  'Comment-cleanup pass: the added doc blocks below are flagged for length, ' +
  'not content. COMPRESS each block to the one or two lines that are genuinely ' +
  'non-recoverable from the code — drop what-summaries, product narrative, and ' +
  'restated signatures. DELETE the block if nothing survives; KEEP it as-is ' +
  'only if every line is load-bearing. A block containing rationale still gets ' +
  'compressed: keep the rationale line, drop the wrapping.';

const BOUNCE_TRAILER =
  'Do not rewrite code, do not add new comments, do not touch comments not ' +
  'listed. Then finish your summary.';

// ---------------------------------------------------------------- comment syntax

const SLASH_EXTS = new Set([
  'js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs', 'mts', 'cts', 'c', 'h', 'cc', 'cpp',
  'hpp', 'java', 'go', 'rs', 'swift', 'kt', 'kts', 'cs', 'php', 'scala', 'dart', 'm',
]);
const HASH_EXTS = new Set([
  'py', 'rb', 'sh', 'bash', 'zsh', 'fish', 'pl', 'pm', 'r', 'yaml', 'yml',
  'toml', 'tf', 'mk', 'ex', 'exs', 'jl',
]);
const DASH_EXTS = new Set(['sql', 'lua', 'hs']);
const BLOCK_ONLY_EXTS = new Set(['css', 'scss', 'less']);

function commentSyntax(file) {
  const base = path.basename(file).toLowerCase();
  if (base === 'makefile' || base === 'dockerfile') return { line: '#' };
  const ext = base.includes('.') ? base.split('.').pop() : '';
  if (SLASH_EXTS.has(ext)) return { line: '//', block: true };
  if (HASH_EXTS.has(ext)) return { line: '#' };
  if (DASH_EXTS.has(ext)) return { line: '--' };
  if (BLOCK_ONLY_EXTS.has(ext)) return { block: true };
  return null;
}

function skippedPath(file) {
  return /\.(md|json|lock|min\.\w+)$/i.test(file) || /database\.types\.ts/.test(file);
}

// ---------------------------------------------------------------- classification

const STARTER_RE =
  /^(first\b|then\b|next\b|now we\b|here we\b|we now\b|let'?s\b|start by\b|loop over\b|iterate\b)/i;

const THIS_X_RE =
  /^this\s+(function|method|hook|file|class|component|script|module)\s+(returns?|takes?|handles?|creates?|loops?|iterates?|checks?|fetches?|gets?|sets?|is|does|will|contains?|defines?|implements?|provides?|processes?|parses?|renders?|calls?|uses?|computes?|calculates?|validates?|updates?|builds?|adds?|removes?|wraps?|stores?|reads?|writes?|maps?|filters?|converts?|extracts?)\b/i;

const EXPORT_RE = /^\s*export\s+(async\s+)?(function|const|let|var|class|default|interface|type|enum)\b/;

const ALLOW_RES = [
  /edge case/i, /\bdo not\b/i, /don'?t/i, /gotcha/i, /workaround/i,
  /\bbecause\b/i, /otherwise/i, /\bnote:/i, /\btodo\b/i, /\bfixme\b/i,
  /\bhack\b/i, /@(link|param|returns?|throws|see|type|typedef)\b/i,
  /eslint-/, /@ts-/, /biome-ignore/, /prettier-ignore/,
  /https?:\/\//, /#\d+/, /\.\w+:\d+/,
];

function allowlisted(stripped) {
  return ALLOW_RES.some((re) => re.test(stripped));
}

function isBanner(trimmed) {
  return /^[/#*\-=~\s]+$/.test(trimmed) && /[=\-*~#]{4}/.test(trimmed);
}

const STOPWORDS = new Set([
  'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'onto', 'are',
  'was', 'were', 'will', 'has', 'have', 'had', 'its', 'all', 'each', 'per',
  'then', 'when', 'out', 'not', 'you', 'our',
]);

function commentWords(stripped) {
  return (stripped.toLowerCase().match(/[a-z]{3,}/g) || []).filter((w) => !STOPWORDS.has(w));
}

function codeFragments(lines) {
  const frags = new Set();
  for (const line of lines) {
    for (const id of line.match(/[A-Za-z_$][A-Za-z0-9_$]*/g) || []) {
      frags.add(id.toLowerCase());
      for (const part of id.split(/[_$]|(?=[A-Z])/)) if (part) frags.add(part.toLowerCase());
    }
  }
  return frags;
}

// Restatement: ≥80% of the comment's significant words already appear as
// identifier fragments in the next three code lines.
function isRestatement(stripped, nextCodeLines) {
  const words = commentWords(stripped);
  if (words.length < 3 || nextCodeLines.length === 0) return false;
  const frags = codeFragments(nextCodeLines);
  let hits = 0;
  for (const w of words) {
    if (frags.has(w) || (w.endsWith('s') && frags.has(w.slice(0, -1)))) { hits++; continue; }
    for (const f of frags) {
      if (f.length >= 3 && (w.startsWith(f) || f.startsWith(w))) { hits++; break; }
    }
  }
  return hits / words.length >= 0.8;
}

// Strip comment markers so heuristics see prose only.
function stripMarker(trimmed, inBlock) {
  let t = trimmed;
  if (inBlock) t = t.replace(/^\*+\s?/, '');
  else t = t.replace(/^(\/\/+|#+|--+|\/\*+)\s*/, '');
  return t.replace(/\*+\/\s*$/, '').trim();
}

// Classify one contiguous run of added lines from a single file.
// Each entry: { line, text }. Returns suspects: { file, line, text, stripped }.
function classifyRun(file, run, syntax, suspects) {
  let inBlock = false;
  const marked = run.map((entry) => {
    const trimmed = entry.text.trim();
    let comment = false;
    let stripped = '';
    if (inBlock) {
      comment = true;
      stripped = stripMarker(trimmed, true);
      if (trimmed.includes('*/')) inBlock = false;
    } else if (syntax.block && trimmed.startsWith('/*')) {
      comment = true;
      stripped = stripMarker(trimmed, false);
      if (!trimmed.includes('*/')) inBlock = true;
    } else if (syntax.line && trimmed.startsWith(syntax.line) && !trimmed.startsWith('#!')) {
      comment = true;
      stripped = stripMarker(trimmed, false);
    }
    return { ...entry, trimmed, comment, stripped, blank: trimmed === '' };
  });

  const flagged = new Set();
  const flag = (i, kind) => {
    if (flagged.has(i)) return;
    flagged.add(i);
    const m = marked[i];
    suspects.push({ file, line: m.line, text: m.trimmed, stripped: m.stripped, kind });
  };

  for (let i = 0; i < marked.length; i++) {
    const m = marked[i];
    if (!m.comment || allowlisted(m.stripped)) continue;
    if (isBanner(m.trimmed)) { flag(i, 'narration'); continue; }
    if (STARTER_RE.test(m.stripped) || THIS_X_RE.test(m.stripped)) { flag(i, 'narration'); continue; }
    const nextCode = [];
    for (let j = i + 1; j < marked.length && nextCode.length < 3; j++) {
      if (!marked[j].comment && !marked[j].blank) nextCode.push(marked[j].text);
    }
    if (isRestatement(m.stripped, nextCode)) flag(i, 'narration');
  }

  // A comment block of ≥4 added lines sitting directly above an added export
  // is flagged for length — it gets the COMPRESS instruction, not delete/keep.
  for (let i = 0; i < marked.length; i++) {
    if (!marked[i].comment) continue;
    let end = i;
    while (end + 1 < marked.length && marked[end + 1].comment) end++;
    const blockLen = end - i + 1;
    const next = marked[end + 1];
    if (blockLen >= 4 && next && EXPORT_RE.test(next.text)) {
      for (let j = i; j <= end; j++) {
        if (!allowlisted(marked[j].stripped)) flag(j, 'doc-block');
      }
    }
    i = end;
  }
}

// ---------------------------------------------------------------- git collection

function git(cwd, args) {
  return execFileSync('git', args, {
    cwd, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'],
  });
}

function inGitRepo(cwd) {
  try { return git(cwd, ['rev-parse', '--is-inside-work-tree']).trim() === 'true'; }
  catch { return false; }
}

// Parse a --unified=0 diff into { file -> [{ line, text }] } of added lines.
function parseAddedLines(diffText) {
  const files = new Map();
  let cur = null;
  let newLine = 0;
  for (const raw of diffText.split('\n')) {
    if (raw.startsWith('+++ ')) {
      const p = raw.slice(4);
      cur = p === '/dev/null' ? null : p.startsWith('b/') ? p.slice(2) : p;
      continue;
    }
    if (raw.startsWith('@@')) {
      const m = /\+(\d+)/.exec(raw);
      newLine = m ? parseInt(m[1], 10) : 0;
      continue;
    }
    if (!cur) continue;
    if (raw.startsWith('+')) {
      if (!files.has(cur)) files.set(cur, []);
      files.get(cur).push({ line: newLine, text: raw.slice(1) });
      newLine++;
    } else if (raw.startsWith(' ')) {
      newLine++;
    }
  }
  return files;
}

function readUntracked(cwd, file) {
  try {
    const full = path.join(cwd, file);
    if (fs.statSync(full).size > 5 * 1024 * 1024) return null;
    const buf = fs.readFileSync(full);
    if (buf.subarray(0, 8000).includes(0)) return null;
    return buf.toString('utf8').split('\n').map((text, i) => ({ line: i + 1, text }));
  } catch { return null; }
}

// Gather added lines (tracked diff + untracked files), classify, and return
// { suspects, skipped, addedLines }. diffArg overrides the default HEAD diff.
function collectSuspects(cwd, diffArg) {
  const perFile = new Map();
  let diffText = '';
  try { diffText = git(cwd, ['diff', diffArg || 'HEAD', '--unified=0', '--no-color']); }
  catch { /* no HEAD yet (fresh repo) — untracked files still scanned below */ }
  for (const [file, entries] of parseAddedLines(diffText)) perFile.set(file, entries);

  if (!diffArg) {
    let untracked = [];
    try { untracked = git(cwd, ['ls-files', '--others', '--exclude-standard', '-z']).split('\0').filter(Boolean); }
    catch { untracked = []; }
    for (const file of untracked) {
      if (skippedPath(file) || !commentSyntax(file)) continue;
      const entries = readUntracked(cwd, file);
      if (entries) perFile.set(file, entries);
    }
  }

  const suspects = [];
  const skipped = [];
  let addedLines = 0;
  for (const [file, entries] of perFile) {
    if (skippedPath(file)) continue;
    const syntax = commentSyntax(file);
    if (!syntax) continue;
    if (entries.length > MAX_ADDED_LINES) { skipped.push(file); continue; }
    addedLines += entries.length;
    let run = [];
    for (const entry of entries) {
      if (run.length && entry.line !== run[run.length - 1].line + 1) {
        classifyRun(file, run, syntax, suspects);
        run = [];
      }
      run.push(entry);
    }
    if (run.length) classifyRun(file, run, syntax, suspects);
  }
  return { suspects, skipped, addedLines };
}

// ---------------------------------------------------------------- state + log

const normalise = (s) => s.toLowerCase().replace(/\s+/g, ' ').trim();
const fingerprint = (s) =>
  crypto.createHash('sha1').update(`${s.file}\0${normalise(s.stripped || s.text)}`).digest('hex');

const stateFile = (sessionId) =>
  path.join(STATE_DIR, `${String(sessionId).replace(/[^\w-]/g, '_')}.json`);

function loadState(sessionId) {
  try { return new Set(JSON.parse(fs.readFileSync(stateFile(sessionId), 'utf8'))); }
  catch { return new Set(); }
}

function saveState(sessionId, set) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    fs.writeFileSync(stateFile(sessionId), JSON.stringify([...set]));
  } catch { /* state is best-effort */ }
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

// Bounce listing: one header per file, its comment lines indented beneath, so
// the comment text stays readable instead of being pushed right by long paths.
function formatListing(suspects) {
  const byFile = new Map();
  for (const s of suspects) {
    if (!byFile.has(s.file)) byFile.set(s.file, []);
    byFile.get(s.file).push(s);
  }
  return [...byFile.entries()]
    .map(([file, group]) =>
      `${file}\n` +
      group
        .sort((a, b) => a.line - b.line)
        .map((s) => `  ${s.line}  ${s.text}`)
        .join('\n'))
    .join('\n\n');
}

const suspectLabels = (suspects) =>
  suspects.map((s) => `${s.file}:${s.line}: [${s.kind || 'narration'}] ${s.stripped || s.text}`);
const suspectFiles = (suspects) => [...new Set(suspects.map((s) => s.file))];

// ---------------------------------------------------------------- turn-type gate

// True when the turn since the last genuine user message used a file-mutating
// tool (Bash counts — it may have written files). Fails open on any doubt.
function turnHasMutation(transcriptPath) {
  try {
    const lines = fs.readFileSync(transcriptPath, 'utf8').split('\n');
    const entries = [];
    for (const line of lines) {
      if (!line.trim()) continue;
      try { entries.push(JSON.parse(line)); } catch { /* skip bad rows */ }
    }
    let lastUser = -1;
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      if (e.type !== 'user' || e.isMeta) continue;
      const content = e.message?.content;
      const genuine = typeof content === 'string' ||
        (Array.isArray(content) && content.some((b) => b?.type === 'text'));
      if (genuine) lastUser = i;
    }
    if (lastUser === -1) return true;
    for (let i = lastUser + 1; i < entries.length; i++) {
      const e = entries[i];
      if (e.type !== 'assistant') continue;
      const content = e.message?.content;
      if (!Array.isArray(content)) continue;
      if (content.some((b) => b?.type === 'tool_use' && MUTATING_TOOLS.has(b.name))) return true;
    }
    return false;
  } catch { return true; }
}

// ---------------------------------------------------------------- modes

function runStop(input) {
  const cwd = input.cwd || process.cwd();
  const sessionId = input.session_id || 'unknown';
  pruneState();

  // Loop guard: already a continuation from a bounce this turn. Log what the
  // model consciously kept, remember it, and never bounce twice.
  if (input.stop_hook_active) {
    if (!inGitRepo(cwd)) { log({ cwd, mode: 'no-git' }); return; }
    const { suspects, skipped } = collectSuspects(cwd);
    const state = loadState(sessionId);
    for (const s of suspects) state.add(fingerprint(s));
    saveState(sessionId, state);
    log({
      cwd, mode: 'residual', flagged: suspects.length,
      files: suspectFiles(suspects), suspects: suspectLabels(suspects), skipped,
    });
    return;
  }

  if (!turnHasMutation(input.transcript_path)) {
    log({ cwd, mode: 'no-mutation', flagged: 0 });
    return;
  }
  if (!inGitRepo(cwd)) { log({ cwd, mode: 'no-git' }); return; }

  const { suspects, skipped } = collectSuspects(cwd);
  const state = loadState(sessionId);
  const fresh = suspects.filter((s) => !state.has(fingerprint(s)));
  if (fresh.length === 0) {
    log({ cwd, mode: 'clean', flagged: 0, skipped });
    return;
  }

  for (const s of fresh) state.add(fingerprint(s));
  saveState(sessionId, state);
  const narration = fresh.filter((s) => s.kind !== 'doc-block');
  const docBlocks = fresh.filter((s) => s.kind === 'doc-block');
  const sections = [];
  if (narration.length) sections.push(`${NARRATION_REASON}\n\n${formatListing(narration)}`);
  if (docBlocks.length) sections.push(`${DOC_BLOCK_REASON}\n\n${formatListing(docBlocks)}`);
  sections.push(BOUNCE_TRAILER);
  process.stdout.write(JSON.stringify({ decision: 'block', reason: sections.join('\n\n') }) + '\n');
  log({
    cwd, mode: 'bounce', flagged: fresh.length,
    files: suspectFiles(fresh), suspects: suspectLabels(fresh), skipped,
  });
}

// SessionStart: fingerprint suspects already sitting in the dirty tree so
// uncommitted leftovers from previous sessions are never bounced on.
function runBaseline(input) {
  const cwd = input.cwd || process.cwd();
  const sessionId = input.session_id || 'unknown';
  pruneState();
  if (!inGitRepo(cwd)) { log({ cwd, mode: 'baseline', flagged: 0 }); return; }
  const { suspects, skipped } = collectSuspects(cwd);
  const state = loadState(sessionId);
  for (const s of suspects) state.add(fingerprint(s));
  saveState(sessionId, state);
  log({
    cwd, mode: 'baseline', flagged: suspects.length,
    files: suspectFiles(suspects), suspects: suspectLabels(suspects), skipped,
  });
}

function runDiffFrom(rev) {
  if (!rev) { process.stderr.write('usage: comment-suspects.mjs --diff-from <rev|A..B>\n'); process.exit(1); }
  const cwd = process.cwd();
  if (!inGitRepo(cwd)) { process.stderr.write('not a git repository\n'); process.exit(1); }
  const { suspects, addedLines } = collectSuspects(cwd, rev);
  process.stdout.write(`ADDED ${addedLines}\n`);
  for (const s of suspects) process.stdout.write(`SUSPECT ${s.file}:${s.line}: [${s.kind}] ${s.text}\n`);
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
  const di = argv.indexOf('--diff-from');
  if (di !== -1) { runDiffFrom(argv[di + 1]); return; }
  const input = await readStdin();
  if (!input || typeof input !== 'object') return;
  if (argv.includes('--baseline-session')) runBaseline(input);
  else runStop(input);
}

main().then(() => process.exit(0)).catch((err) => {
  // A broken hook must not brick every session.
  log({ mode: 'error', error: String(err && err.message || err) });
  process.exit(0);
});
