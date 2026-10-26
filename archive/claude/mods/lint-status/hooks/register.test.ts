import type { On, ProcessRunResult } from 'claude-code'
import { expect, mock, test, type Engine } from 'claude-code/testing'
import { parseProblemCount } from './register'

const KIT = '/home/me/.claude/lint/kit.sh'
const SNAPSHOT = '/home/me/.claude/lint/projects/abc/def.suppressions.json'

const STYLISH_THREE = `
/repo/src/a.ts
  4:1  error  Function has too many lines  max-lines-per-function
  9:3  error  Unexpected any               @typescript-eslint/no-explicit-any

/repo/src/b.ts
  1:1  error  File has too many lines  max-lines

✖ 3 problems (3 errors, 0 warnings)
`

function ran(stdout: string, exitCode = 0, stderr = ''): ProcessRunResult {
  return { exitCode, stdout, stderr, isStdoutTruncated: false, isStderrTruncated: false }
}

function answer(result: ProcessRunResult) {
  return { value: result }
}

type World = { porcelain: string; snapshotExists: boolean; check?: ProcessRunResult }

function stubWorld(on: On, world: World) {
  mock.env(on, { HOME: '/home/me' })
  on('session.cwd', () => ({ value: '/repo' }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.exists', ($, e) => ({ value: e.path === SNAPSHOT && world.snapshotExists }))
  const commands: string[] = []
  on('process.run', ($, e) => {
    const argv = e.argv.join(' ')
    commands.push(argv)
    if (argv === 'git status --porcelain') return answer(ran(world.porcelain))
    if (argv === `${KIT} --cwd /repo paths`) return answer(ran(`repo_key=abc\nworktree_key=def\nsnapshot=${SNAPSHOT}\n`))
    if (argv === `${KIT} --cwd /repo check` && world.check) return answer(world.check)
    throw new Error(`unexpected command: ${argv}`)
  })

  const statuses: (string | undefined)[] = []
  const toasts: string[] = []
  let settle: () => void = () => {}
  const settled = new Promise<void>(resolve => (settle = resolve))
  on('ui.status', ($, e) => {
    statuses.push(e.text)
    settle()
    return { value: undefined }
  })
  on('ui.toast', ($, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  return { statuses, toasts, commands, settled }
}

async function completeTurn($: Engine) {
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
}

test('parses the problem count from the stylish summary', () => {
  expect(parseProblemCount(STYLISH_THREE)).toBe(3)
  expect(parseProblemCount('✖ 1 problem (1 error, 0 warnings)\n')).toBe(1)
  expect(parseProblemCount('\x1b[31m\x1b[1m✖ 12 problems (12 errors, 0 warnings)\x1b[22m\x1b[39m')).toBe(12)
  expect(parseProblemCount('')).toBeUndefined()
  expect(parseProblemCount('Oops! Something went wrong!')).toBeUndefined()
})

test('a clean tree clears the status without running the kit', async ($, on) => {
  const world = stubWorld(on, { porcelain: '', snapshotExists: true })
  await completeTurn($)
  await world.settled
  expect(world.statuses).toEqual([undefined])
})

test('a dirty tree with no snapshot on disk says no snapshot', async ($, on) => {
  const world = stubWorld(on, { porcelain: ' M src/a.ts\n', snapshotExists: false })
  await completeTurn($)
  await world.settled
  expect(world.statuses).toEqual(['lint: no snapshot'])
})

test('violations above the snapshot are counted', async ($, on) => {
  const world = stubWorld(on, { porcelain: ' M src/a.ts\n', snapshotExists: true, check: ran(STYLISH_THREE, 1) })
  await completeTurn($)
  await world.settled
  expect(world.statuses).toEqual(['lint: +3 above snapshot'])
})

test('a passing check clears the status', async ($, on) => {
  const world = stubWorld(on, { porcelain: '?? new.ts\n', snapshotExists: true, check: ran('') })
  await completeTurn($)
  await world.settled
  expect(world.statuses).toEqual([undefined])
})

test('an unparseable failure says check failed and toasts the first stderr line', async ($, on) => {
  const failure = ran('', 1, 'lint kit: not installed. Run: cd ~/.claude/lint && npm install\n')
  const world = stubWorld(on, { porcelain: ' M src/a.ts\n', snapshotExists: true, check: failure })
  await completeTurn($)
  await world.settled
  expect(world.statuses).toEqual(['lint: check failed'])
  expect(world.toasts).toEqual(['lint kit: not installed. Run: cd ~/.claude/lint && npm install'])
})

test('session start runs the check with no placeholder', async ($, on) => {
  const world = stubWorld(on, { porcelain: '', snapshotExists: true })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  await world.settled
  expect(world.statuses).toEqual([undefined])
})

test('subagent and aborted turns are skipped', async ($, on) => {
  const world = stubWorld(on, { porcelain: '', snapshotExists: true })
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer', agentId: 'a1' })
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: true, turnId: 't3', reason: 'aborted' })
  await completeTurn($)
  await world.settled
  expect(world.commands).toEqual(['git status --porcelain'])
  expect(world.statuses).toEqual([undefined])
})
