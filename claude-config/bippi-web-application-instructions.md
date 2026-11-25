The instruction files checked into this repo describe the project and were
written for agents that work unattended. In a local session the user creates
the branches and pushes by hand, and a pull request is opened when the user
asks for one here. The session commits only the commits of a build plan the
user has approved, each once its check passes; any other change is left for
the user to commit.

The running app is checked with Playwright against the dev server the user
runs from this checkout.

A code graph of this repo's default branch is at
~/graphify-graphs/bippi-web-application/graph.json. To find code you have not
been pointed to, query the graph before searching:
`graphify query "<names>" --graph ~/graphify-graphs/bippi-web-application/graph.json --budget 4000`,
`graphify explain "<name>" --graph ~/graphify-graphs/bippi-web-application/graph.json` and
`graphify affected "<name>" --graph ~/graphify-graphs/bippi-web-application/graph.json`.
Query by concrete names such as a file path or a function name, because
matching is by keyword. Open each file the graph points to before relying on
it, and search normally for code that exists only on a branch, because the
graph does not have it.
