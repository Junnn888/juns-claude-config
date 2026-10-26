import { expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On, PromptComposeInput } from 'claude-code'

const DEFAULT_NOTE =
  'The prompt-tweaks mod is active in this session. If the user asks which mods are active, say that prompt-tweaks is.'

const ENGINE_SECTIONS = [
  { id: 'intro', text: 'engine intro', scope: 'shared' },
  { id: 'env', text: 'engine env', scope: 'session' },
] as const

const COMPOSE_INPUT: PromptComposeInput = {
  model: 'claude-test',
  promptModel: 'claude-test',
  surfaces: [],
  tools: [],
  outputStyle: null,
  traits: [],
}

async function compose($: Engine, on: On) {
  on('prompt.compose', () => ({ sections: ENGINE_SECTIONS }))
  const { sections } = await $.prompt.compose(COMPOSE_INPUT)
  return sections
}

function engineSubmit($: Engine, on: On) {
  const toasts: string[] = []
  on('ui.toast', ($, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('prompt.submit', ($, e) => ({ text: e.text }))
  const submit = async (text: string) => {
    const result = await $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
    return 'text' in result ? result.text : undefined
  }
  return { submit, toasts }
}

test('compose appends one session section with the default note', async ($, on) => {
  expect(await compose($, on)).toEqual([
    ...ENGINE_SECTIONS,
    { id: 'prompt-tweaks:note', text: DEFAULT_NOTE, scope: 'session' },
  ])
})

test('compose appends nothing when the note is empty', { options: { note: '' } }, async ($, on) => {
  expect(await compose($, on)).toEqual(ENGINE_SECTIONS)
})

test('submit expands a trailing :why and toasts', async ($, on) => {
  const { submit, toasts } = engineSubmit($, on)
  expect(await submit('fix the bug :why')).toBe(
    'fix the bug State the cause first, then the evidence chain, then the fix as the last step.',
  )
  expect(toasts).toEqual(['expanded :why'])
})

test('submit expands :short and :opts', async ($, on) => {
  const { submit, toasts } = engineSubmit($, on)
  expect(await submit('summarise :short')).toBe('summarise Answer in at most three lines.')
  expect(await submit('which db? :opts')).toBe(
    'which db? Give ranked options, recommendation first, one line of trade-off each.',
  )
  expect(toasts).toEqual(['expanded :short', 'expanded :opts'])
})

test('submit leaves slash commands and plain text alone', async ($, on) => {
  const { submit, toasts } = engineSubmit($, on)
  expect(await submit('/walk :why')).toBe('/walk :why')
  expect(await submit('plain text')).toBe('plain text')
  expect(toasts).toEqual([])
})

test('submit ignores a token that is not trailing, not whitespace-separated or unknown', async ($, on) => {
  const { submit, toasts } = engineSubmit($, on)
  expect(await submit('explain :why this fails')).toBe('explain :why this fails')
  expect(await submit('see foo:why')).toBe('see foo:why')
  expect(await submit('hello :nope')).toBe('hello :nope')
  expect(toasts).toEqual([])
})
