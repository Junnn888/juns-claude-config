import type { EngineInterface, Register } from 'claude-code'

// ESLint's stylish formatter ends with "✖ 3 problems (3 errors, 0 warnings)".
const PROBLEM_SUMMARY = /✖ (\d+) problems? \(/
const ANSI = /\x1b\[[0-9;]*m/g
const CHECK_TIMEOUT_MS = 120_000

export function parseProblemCount(output: string): number | undefined {
  const match = PROBLEM_SUMMARY.exec(output.replace(ANSI, ''))
  return match ? Number(match[1]) : undefined
}

type Outcome = { status: string | undefined; toast?: string }

// A good outcome clears the line: the status only shows when lint needs attention.
async function lintOutcome($: EngineInterface, cwd: string): Promise<Outcome> {
  const home = await $.env.get('HOME')
  if (home === undefined) return { status: undefined }
  const kit = `${home}/.claude/lint/kit.sh`

  const tree = await $.process.run(['git', 'status', '--porcelain'], { cwd })
  if (tree.exitCode !== 0) return { status: undefined }
  if (tree.stdout.trim() === '') return { status: undefined }

  // `paths` prints nothing outside a git worktree with a package.json: not a kit project.
  const paths = await $.process.run([kit, '--cwd', cwd, 'paths'])
  const snapshot = /^snapshot=(.+)$/m.exec(paths.stdout)?.[1]
  if (snapshot === undefined) return { status: undefined }
  // `check` takes the snapshot itself when it is missing; leave that to lint-baseline.sh.
  if (!(await $.fs.exists(snapshot))) return { status: 'lint: no snapshot' }

  const check = await $.process.run([kit, '--cwd', cwd, 'check'], { timeoutMs: CHECK_TIMEOUT_MS })
  const count = parseProblemCount(check.stdout)
  if (count !== undefined && count > 0) return { status: `lint: +${count} above snapshot` }
  if (check.exitCode === 0) return { status: undefined }
  return { status: 'lint: check failed', toast: check.stderr.split('\n').find(line => line.trim() !== '') }
}

// A slow check from an earlier turn must not overwrite a newer result.
let latestRun = 0

async function refresh($: EngineInterface, cwd: string): Promise<void> {
  const run = ++latestRun
  let outcome: Outcome
  try {
    outcome = await lintOutcome($, cwd)
  } catch {
    // The kit or git could not start: nothing to report for this directory.
    outcome = { status: undefined }
  }
  if (run !== latestRun) return
  $.ui.status(outcome.status)
  if (outcome.toast !== undefined) $.ui.toast(outcome.toast)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    void refresh($, e.cwd)
    return started
  })

  on('turn.complete', async ($, e, next) => {
    const completed = await next(e)
    if (e.agentId === undefined && !e.isAborted) void refresh($, await $.session.cwd())
    return completed
  })
}
