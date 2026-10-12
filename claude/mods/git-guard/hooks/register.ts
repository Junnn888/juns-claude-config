import type { Register } from 'claude-code'

// Ported from claude/hooks/safety-bash.sh (version-control category only).
const CMD_POS = String.raw`(^|[;&|(])\s*([a-z_][a-z0-9_]*=\S*\s+)*`
const GIT_FLAGS = String.raw`(\s+-\S+(\s+[^-\s]\S*)?)*`

const STATE_CHANGE = new RegExp(`${CMD_POS}git${GIT_FLAGS}\\s+(commit|add|push|reset|rebase|clean)(\\s|$)`)
const FORCE_PUSH = /git\s+push.*(--force|-f)(\s|$)/
const DISCARD = /git\s+(checkout|restore)\s+(\.|--)/

const stripQuoted = (line: string) => line.replace(/'[^']*'/g, '').replace(/"[^"]*"/g, '')

// grep and sed work line by line, so every rule is tested per line to keep their anchors and quote spans.
const anyLine = (lines: string[], rule: RegExp) => lines.some(line => rule.test(line))

const blockMessage = (reason: string) =>
  [
    `BLOCKED (version-control): ${reason}`,
    "This is the user's manual step. Do NOT retry or work around it.",
    'Surface the exact command so the user can run it themselves outside the agent.',
  ].join('\n')

const blockReason = (command: string): string | undefined => {
  const lines = command.toLowerCase().split('\n')
  if (anyLine(lines.map(stripQuoted), STATE_CHANGE)) return "git state changes are the user's call"
  if (anyLine(lines, FORCE_PUSH)) return 'force-push is destructive and user-only'
  if (anyLine(lines, DISCARD)) return 'discarding working-tree changes is user-only'
  return undefined
}

export const register: Register = on => {
  on('tool.call', { tool: 'Bash' }, ($, e, next) => {
    const reason = blockReason(e.command)
    return reason === undefined ? next(e) : { deny: blockMessage(reason) }
  })
}
