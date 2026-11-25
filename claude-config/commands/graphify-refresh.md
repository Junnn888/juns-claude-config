---
description: Rebuild the code graph for the project this session is in, from its default branch
argument-hint: "[--force]"
disable-model-invocation: true
allowed-tools: Bash(~/.claude/scripts/graph-refresh.sh:*)
---

Refresh result: !`~/.claude/scripts/graph-refresh.sh $ARGUMENTS 2>&1`

The refresh has already run; the line above is its output. It works from the
main checkout or any worktree, and it reads the default branch from the remote,
so the branch checked out here does not matter.

Reply with the result in one or two plain sentences and stop. Run nothing else.

- "already at": say the graph was current and nothing was rebuilt. `--force`
  rebuilds anyway.
- "rebuilt from": give the commit, the node count and the time taken.
- An error: quote it and name the log file it points to.
