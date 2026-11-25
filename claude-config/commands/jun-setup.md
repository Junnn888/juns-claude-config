---
description: "Set up a repo for local sessions, once, in its main checkout: print the lines in its instruction files written for autonomous agents, then write one shared instructions file under ~/.claude and a git-ignored CLAUDE.local.md that imports it"
disable-model-invocation: true
allowed-tools: Bash(git rev-parse:*), Bash(git check-ignore:*), Bash(git status:*), Bash(grep:*), Bash(ls:*), Bash(pwd:*)
---

Current folder: !`pwd`
Top level: !`git rev-parse --show-toplevel 2>/dev/null || echo NONE`
Shared git folder: !`git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo NONE`
Tree before: !`git status --short 2>/dev/null || echo NONE`
Instruction files in the current folder: !`ls CLAUDE.md AGENTS.md CLAUDE.local.md 2>/dev/null || echo none`
Lines that mention git, the remote or working unasked: !`grep -n -i -E 'branch|rebase|push|pull request|commit|merge|worktree|without asking|do not ask|proceed' CLAUDE.md AGENTS.md 2>/dev/null || echo none`

A repo's own `CLAUDE.md` or `AGENTS.md` is often written for agents that work
unattended: they branch, commit and push by themselves. This command adds a
local note that those lines are for unattended agents, and records how this
repo's running app is checked. It changes no tracked file.

If the top level is `NONE`, say this is not a git repo and stop. If the
current folder is not the top level, ask the user to run the command from the
top level and stop, because the lists above were read from the current folder.

The main checkout is the folder that holds the shared git folder; the project
name is that folder's name in lower case with hyphens. The shared file is
`~/.claude/<project>-instructions.md`. If it already exists, show it and stop,
because the command runs once per repo and the file is then the user's to edit.

## 1. Print the lines written for autonomous agents

From the lines listed above, print the ones that tell an agent to act on git
or the remote by itself, or to carry on without asking, each with its file and
line number. Leave out lines that only describe a convention, such as a commit
message format. The user reads this list to see what the repo asks of an agent.

## 2. Show both files, then wait

Show the user both files in full and wait for a yes, so nothing is written
that they have not read.

The shared file:

```markdown
The instruction files checked into this repo describe the project and were
written for agents that work unattended. In a local session the user creates
the branches and pushes by hand, and a pull request is opened when the user
asks for one here. The session commits only the commits of a build plan the
user has approved, each once its check passes; any other change is left for
the user to commit.

The running app is checked with <method>.
```

For `<method>`, propose one sentence from what the repo's instruction files
and scripts say, for example "Playwright against the dev server the user runs
with `bun dev` at http://localhost:3000". If they say nothing, ask the user in
the same reply. If the user has no method yet, leave that sentence out and
tell them the repo then names no way to check the running app.

`CLAUDE.local.md` at the top level:

```markdown
@~/.claude/<project>-instructions.md
@AGENTS.md
```

Include the `@AGENTS.md` line only when `AGENTS.md` exists at the top level
and `CLAUDE.md` does not already import it: once a `CLAUDE.local.md` exists,
Claude Code stops reading `AGENTS.md` by itself.

## 3. Write

- Write the shared file yourself; it is config under `~/.claude`.
- Run `git check-ignore -q CLAUDE.local.md` yourself. Then send one `patch` to
  write `CLAUDE.local.md` and, if that command exited non-zero, to add the
  line `CLAUDE.local.md` to `<shared git folder>/info/exclude`. Its check is
  `git status --short --ignored CLAUDE.local.md`, which prints
  `!! CLAUDE.local.md` when git ignores the file. If the write to the exclude
  file is refused, give the user the line to add there themselves.

## 4. Report

- Each path written.
- "No tracked file was changed", with `git status --short` now beside the
  tree before as the evidence.
- The lines from step 1 again.
- What the user does next: restart the session so the new file loads, approve
  the import when Claude Code asks about it the first time, and copy
  `CLAUDE.local.md` into each existing or new worktree.
