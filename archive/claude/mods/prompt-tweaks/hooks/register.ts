import type { PromptComposeSection, Register } from 'claude-code'

const EXPANSIONS: Readonly<Record<string, string>> = {
  ':short': 'Answer in at most three lines.',
  ':why': 'State the cause first, then the evidence chain, then the fix as the last step.',
  ':opts': 'Give ranked options, recommendation first, one line of trade-off each.',
}

const TRAILING_TOKEN = /(^|\s)(:[a-z]+)\s*$/

function expandShorthand(text: string): { text: string; token: string } | undefined {
  if (text.startsWith('/')) return undefined
  const match = TRAILING_TOKEN.exec(text)
  const token = match?.[2]
  if (match === null || token === undefined) return undefined
  const expansion = EXPANSIONS[token]
  if (expansion === undefined) return undefined
  return { text: text.slice(0, match.index) + (match[1] ?? '') + expansion, token }
}

export const register: Register = (on, options) => {
  const note = typeof options.note === 'string' ? options.note : ''

  on('prompt.compose', async ($, e, next) => {
    if (note === '') return next(e)
    const r = await next(e)
    const mine: PromptComposeSection = { id: 'prompt-tweaks:note', text: note, scope: 'session' }
    return { sections: [...r.sections, mine] }
  })

  on('prompt.submit', ($, e, next) => {
    const expanded = expandShorthand(e.text)
    if (expanded === undefined) return next(e)
    $.ui.toast(`expanded ${expanded.token}`)
    return next({ ...e, text: expanded.text })
  })
}
