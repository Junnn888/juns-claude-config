import type { Block, Snip } from '../types'

export const MAX_SNIPS = 50

const OPENER = /^( {0,3})(`{3,}|~{3,})(.*)$/
const CLOSER = /^ {0,3}(`{3,}|~{3,})[ \t]*$/

// CommonMark fences: the closer repeats the opener's character at least as many
// times, and an opener's indent (up to 3 spaces) is taken off each body line.
export function extractBlocks(answer: string): Block[] {
  const lines = answer.split('\n')
  const blocks: Block[] = []
  let at = 0

  while (at < lines.length) {
    const open = OPENER.exec(lines[at] ?? '')
    const [, indent = '', fence = '', info = ''] = open ?? []
    if (open === null || (fence[0] === '`' && info.includes('`'))) {
      at++
      continue
    }

    const close = lines.findIndex((line, i) => {
      if (i <= at) return false
      const run = CLOSER.exec(line)?.[1]
      return run !== undefined && run[0] === fence[0] && run.length >= fence.length
    })
    if (close === -1) break

    const dedent = new RegExp(`^ {0,${indent.length}}`)
    blocks.push({
      lang: info.trim().split(/\s+/)[0] ?? '',
      body: lines
        .slice(at + 1, close)
        .map(line => line.replace(dedent, ''))
        .join('\n'),
    })
    at = close + 1
  }

  return blocks
}

export function toSnips(blocks: Block[], turn: string, at: number): Snip[] {
  return blocks.map((block, i) => ({
    ...block,
    id: `${turn}:${i}`,
    firstLine: block.body.split('\n').find(line => line.trim() !== '')?.trim() ?? '',
    turn,
    at,
  }))
}

export const prepend = (added: Snip[], kept: Snip[]): Snip[] => [...added, ...kept].slice(0, MAX_SNIPS)

export const lineCount = (body: string) => (body === '' ? 0 : body.split('\n').length)

export const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`

export const copiedLine = (snip: Snip) => `copied ${snip.lang || 'text'} · ${plural(lineCount(snip.body), 'line')}`

export const truncate = (text: string, width: number) =>
  text.length <= width ? text : width <= 0 ? '' : `${text.slice(0, width - 1)}…`

// `/copy` takes an optional 1-based index; anything else names no snippet.
export function snipIndex(args: string): number | undefined {
  const arg = args.trim()
  if (arg === '') return 0
  return /^[1-9]\d*$/.test(arg) ? Number(arg) - 1 : undefined
}
