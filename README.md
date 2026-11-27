# Claude Code config

The live config is in `~/.claude`. The `claude-config/` folder here is its mirror.

## Plugins

`claude-config/settings.json` turns on these two plugins. Both are user-scope plugins from the built-in `anthropic-plugin-directory` marketplace. On a new machine, install them in Claude Code:

| Plugin | Install | After installing |
|---|---|---|
| `coderabbit` | `/plugin install coderabbit@anthropic-plugin-directory` | Sign in with `/coderabbit:setup` |
| `frontend-design` | `/plugin install frontend-design@anthropic-plugin-directory` | Nothing |

Or open `/plugin`, find each one under the plugin directory, and install it at user scope. Restart Claude Code once both are in.
