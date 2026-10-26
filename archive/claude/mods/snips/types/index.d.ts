export type Block = { lang: string; body: string }
export type Snip = Block & { id: string; firstLine: string; turn: string; at: number }

declare module 'claude-code' {
  interface PluginState {
    snips: { snips: Snip[] }
  }
}
