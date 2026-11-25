The instruction files checked into this repo describe the project and were
written for agents that work unattended. In a local session the user creates
the branches and pushes by hand, and a pull request is opened when the user
asks for one here. The session commits only the commits of a build plan the
user has approved, each once its check passes; any other change is left for
the user to commit.

The running app is checked with Playwright against the dev server the user
runs with `bun dev`. Each checkout runs its own server on the `PORT` in its
`.env.local`. Find this checkout's server with `bun run dev:port`, which
prints its URL or exits 1 when this checkout has none running. In a checkout
without that script, read `.next/dev/lock` and check its `pid` is alive.

A code graph of this repo's main branch is at
~/graphify-graphs/biologic-cellular/graph.json. To find code you have not
been pointed to, query the graph before searching:
`graphify query "<names>" --graph ~/graphify-graphs/biologic-cellular/graph.json --budget 4000`,
`graphify explain "<name>" --graph ~/graphify-graphs/biologic-cellular/graph.json` and
`graphify affected "<name>" --graph ~/graphify-graphs/biologic-cellular/graph.json`.
Query by concrete names such as a file path or a function name, because
matching is by keyword. Open each file the graph points to before relying on
it, and search normally for code that exists only on a branch, because the
graph does not have it.
