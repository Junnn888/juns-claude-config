import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderSurface } from 'claude-code'

import type { Snip } from '../types'
import { copiedLine, extractBlocks, lineCount, plural, prepend, snipIndex, toSnips, truncate } from './snips'

const PANE = 'snips'
const snips = atom({ plugin: 'snips', key: 'snips' } as const, [] as Snip[])

// `[ Copy ]` and `[ Drop ]` with a one-cell gap before each.
const BUTTONS_WIDTH = 18

async function copySnip($: EngineInterface, snip: Snip, surface?: RenderSurface): Promise<string> {
  const copied = await $.ui.copy({ text: snip.body, surface })

  return copied.isCopied ? copiedLine(snip) : `copy failed: ${copied.reason}`
}

async function copyById($: EngineInterface, id: string, surface: RenderSurface) {
  const snip = (await read($, snips)).find(s => s.id === id)
  if (snip !== undefined) $.ui.toast(await copySnip($, snip, surface))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'snips',
      description: 'Pane of code blocks from recent answers, with Copy buttons',
    })
    await $.command.register({
      name: 'copy',
      description: 'Copy snippet n (newest first, default 1) to the clipboard untouched',
    })

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined && !e.isAborted) {
      const added = toSnips(extractBlocks(e.answer), e.turnId, await $.clock.now())
      if (added.length > 0) {
        await update($, snips, kept => prepend(added, kept))
        const isShown = (await $.ui.panes()).some(pane => pane.id === PANE && pane.isShown)
        if (!isShown) $.ui.toast(`${plural(added.length, 'snippet')} saved: /snips`)
      }
    }

    return next(e)
  })

  on('command.run', { command: 'snips' }, async $ => {
    const saved = await read($, snips)
    await $.ui.open({ id: PANE, title: 'Snippets' })

    return { text: `Snippets: ${saved.length} saved` }
  })

  on('command.run', { command: 'copy' }, async ($, e) => {
    const index = snipIndex(e.args)
    const snip = index === undefined ? undefined : (await read($, snips))[index]
    if (snip === undefined) return { text: `no snippet ${e.args.trim() || '1'}` }

    return { text: await copySnip($, snip) }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const saved = await read($, snips)

    if (saved.length === 0) {
      return <Text dimColor>No code blocks yet. They appear here after an answer contains one.</Text>
    }

    return (
      <Box flexDirection="column">
        <Text bold>{`${plural(saved.length, 'snippet')} · newest first`}</Text>
        {saved.map((snip, i) => {
          const label = `${i + 1}. ${snip.lang || 'text'} · ${plural(lineCount(snip.body), 'line')} · `
          const room = e.props.bodyColumns - label.length - BUTTONS_WIDTH

          return (
            <Box key={snip.id} flexDirection="row" gap={1}>
              <Text wrap="truncate">{label + truncate(snip.firstLine, room)}</Text>
              <Button
                key={`copy:${snip.id}`}
                label="Copy"
                onPress={press => copyById($, snip.id, press.surface)}
              />
              <Button
                key={`drop:${snip.id}`}
                label="Drop"
                onPress={() => update($, snips, now => now.filter(s => s.id !== snip.id))}
              />
            </Box>
          )
        })}
        <Button key="clear" label="Clear all" onPress={() => update($, snips, () => [])} />
      </Box>
    )
  })
}
