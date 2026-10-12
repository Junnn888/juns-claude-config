import { expect, test } from 'claude-code/testing'

import { MAX_SNIPS, extractBlocks, prepend, toSnips } from './snips'

test('a sql block keeps the leading spaces on every line', () => {
  const body = '  SELECT id\n    FROM users\n      WHERE active'
  expect(extractBlocks(`Here:\n\`\`\`sql\n${body}\n\`\`\`\nDone.`)).toEqual([{ lang: 'sql', body }])
})

test('two blocks come out in answer order', () => {
  const answer = '```ts\nconst a = 1\n```\ntext between\n```\nplain\n```\n'
  expect(extractBlocks(answer)).toEqual([
    { lang: 'ts', body: 'const a = 1' },
    { lang: '', body: 'plain' },
  ])
})

test('tilde fences close only on tildes', () => {
  const answer = '~~~python\ndef f():\n    return 1\n```\n~~~'
  expect(extractBlocks(answer)).toEqual([{ lang: 'python', body: 'def f():\n    return 1\n```' }])
})

test('a shorter fence inside a longer one is body, not the terminator', () => {
  const inner = '```js\nx()\n```'
  expect(extractBlocks(`\`\`\`\`md\n${inner}\n\`\`\`\``)).toEqual([{ lang: 'md', body: inner }])
})

test('an indented fence strips its indent from each body line', () => {
  const answer = '1. Step\n   ```sh\n   cd app\n     npm test\n  half\n   ```'
  expect(extractBlocks(answer)).toEqual([{ lang: 'sh', body: 'cd app\n  npm test\nhalf' }])
})

test('an unterminated fence is ignored', () => {
  expect(extractBlocks('```ts\nconst a = 1\n``\nno close')).toEqual([])
  expect(extractBlocks('```a\nkept\n```\n```b\nlost')).toEqual([{ lang: 'a', body: 'kept' }])
})

test('the 51st snip drops the oldest', () => {
  let kept = toSnips([{ lang: 'x', body: 'oldest' }], 't0', 0)
  for (let turn = 1; turn < MAX_SNIPS; turn++) kept = prepend(toSnips([{ lang: 'x', body: `b${turn}` }], `t${turn}`, turn), kept)
  expect(kept).toHaveLength(MAX_SNIPS)
  expect(kept[MAX_SNIPS - 1]?.body).toBe('oldest')

  kept = prepend(toSnips([{ lang: 'x', body: 'newest' }], 't50', 50), kept)
  expect(kept).toHaveLength(MAX_SNIPS)
  expect(kept[0]?.body).toBe('newest')
  expect(kept.some(s => s.body === 'oldest')).toBe(false)
})
