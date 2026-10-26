import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

const SQL = '  SELECT id\n    FROM users'
const SH = 'cd app\n  npm test'
const ANSWER = `Two blocks:\n\`\`\`sql\n${SQL}\n\`\`\`\nand\n\`\`\`sh\n${SH}\n\`\`\`\n`

// The engine's side of every call the plugin makes, with the copies and toasts kept.
const world = (on: On) => {
  const copied: string[] = []
  const toasts: string[] = []
  mock.clock(on, { now: 1_000 })
  on('ui.open', () => ({ value: { isPlaced: true as const } }))
  on('ui.panes', () => ({ value: [] }))
  on('ui.toast', (_$, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.copy', (_$, e) => {
    copied.push(e.text)
    return { value: { isCopied: true as const } }
  })
  on('turn.complete', () => ({ text: '' }))
  return { copied, toasts }
}

const TURN = { durationMs: 10, isAborted: false, turnId: 'turn-1', reason: 'answer' as const }

const command = (name: string, args = '') => ({
  command: name,
  args,
  origin: { kind: 'composer' as const },
  presentation: { isFullscreen: true, columns: 120 },
})

const PANE_PROPS = {
  title: 'Snippets',
  isFocused: true,
  bodyColumns: 80,
  placement: 'dock' as const,
  scroll: { offset: 0, bodyRows: 40 },
  view: {},
}

test('a turn with two blocks saves two and toasts once', async ($, on) => {
  const { toasts } = world(on)
  await $.turn.complete({ ...TURN, answer: ANSWER })

  expect(toasts).toEqual(['2 snippets saved: /snips'])
  expect((await $.command.run(command('snips'))).text).toBe('Snippets: 2 saved')
})

test('a subagent or aborted turn saves nothing', async ($, on) => {
  const { toasts } = world(on)
  await $.turn.complete({ ...TURN, answer: ANSWER, agentId: 'a1' })
  await $.turn.complete({ ...TURN, answer: ANSWER, isAborted: true, reason: 'aborted' })

  expect(toasts).toEqual([])
  expect((await $.command.run(command('snips'))).text).toBe('Snippets: 0 saved')
})

test('/copy 2 copies the second body exactly', async ($, on) => {
  const { copied } = world(on)
  await $.turn.complete({ ...TURN, answer: ANSWER })

  expect((await $.command.run(command('copy', '2'))).text).toBe('copied sh · 2 lines')
  expect(copied).toEqual([SH])
  expect((await $.command.run(command('copy'))).text).toBe('copied sql · 2 lines')
  expect(copied[1]).toBe(SQL)
  expect((await $.command.run(command('copy', '3'))).text).toBe('no snippet 3')
  expect((await $.command.run(command('copy', 'x'))).text).toBe('no snippet x')
})

test('the pane lists rows and Copy copies the exact body on the terminal', async ($, on) => {
  const { copied, toasts } = world(on)
  await $.turn.complete({ ...TURN, answer: ANSWER })
  await $.command.run(command('snips'))

  const ui = await $.ui.mount({ plugin: 'snips', surface: 'terminal', component: 'Pane', requestId: 'snips', props: PANE_PROPS })
  expect((await ui.find({ type: 'Text', text: /newest first$/ }))?.text).toBe('2 snippets · newest first')
  expect((await ui.find({ type: 'Text', text: /^1\. / }))?.text).toBe('1. sql · 2 lines · SELECT id')
  expect((await ui.find({ type: 'Text', text: /^2\. / }))?.text).toBe('2. sh · 2 lines · cd app')

  await ui.press({ key: 'copy:turn-1:0' })
  expect(copied).toEqual([SQL])
  expect(toasts.at(-1)).toBe('copied sql · 2 lines')

  await ui.press({ key: 'drop:turn-1:0' })
  expect(await ui.find({ type: 'Text', text: /^2\. / })).toBeUndefined()

  await ui.press({ key: 'clear' })
  expect(await ui.find({ type: 'Text', text: /^No code blocks yet/ })).toBeDefined()

  await ui.unmount()
})
