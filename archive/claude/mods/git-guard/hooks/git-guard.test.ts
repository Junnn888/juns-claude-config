import { describe, expect, test } from 'claude-code/testing'

const STATE = "git state changes are the user's call"
const DISCARD = 'discarding working-tree changes is user-only'

// `git push --force` hits the state-change rule first, as in the shell hook.
const denied: [string, string][] = [
  ['git commit -m x', STATE],
  ['git -C foo push', STATE],
  ['GIT_DIR=x git add .', STATE],
  ['echo hi; git rebase main', STATE],
  ['git push --force', STATE],
  ['git checkout .', DISCARD],
  ['git restore --staged', DISCARD],
]

const allowed = ['git status', 'git log --oneline', 'echo "git commit"', 'git commit-tree', 'ls']

const expectedDeny = (reason: string) =>
  [
    `BLOCKED (version-control): ${reason}`,
    "This is the user's manual step. Do NOT retry or work around it.",
    'Surface the exact command so the user can run it themselves outside the agent.',
  ].join('\n')

describe('denied', () => {
  for (const [command, reason] of denied) {
    test(command, async ($, on) => {
      let hasRun = false
      on('tool.call', { tool: 'Bash' }, () => {
        hasRun = true
        return { result: { stdout: '', stderr: '', interrupted: false } }
      })
      const ran = await $.tool.call({ tool: 'Bash', command })
      expect(hasRun).toBe(false)
      expect(ran.deny).toBe(expectedDeny(reason))
    })
  }
})

describe('allowed', () => {
  for (const command of allowed) {
    test(command, async ($, on) => {
      let seen: string | undefined
      on('tool.call', { tool: 'Bash' }, ($, e) => {
        seen = e.command
        return { result: { stdout: 'ran', stderr: '', interrupted: false } }
      })
      const ran = await $.tool.call({ tool: 'Bash', command })
      expect(ran.deny).toBeUndefined()
      expect(ran.isError).toBeUndefined()
      expect(seen).toBe(command)
    })
  }
})
