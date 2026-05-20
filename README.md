# juns-claude-config

A lean, portable Claude Code config. One curl on a fresh machine installs a
provenance-traced global `CLAUDE.md`, a deny-list + safety hooks, a manual
learnings log, and a self-authored LSP layer. Designed from Anthropic's
official guidance and critically evaluated against (not copied from) gstack.

Philosophy: **few things, each one justified.** Every component had to catch
a failure nothing else does, or it wasn't built. That's why this is small.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

Backs up any existing `~/.claude` to `~/.claude.backup.<timestamp>` first.

## After install

The install script handled the file copies, hook setup, LSP marketplace and
plugin registration, and ran the binary doctor (which printed any missing
language-server binaries with their install commands). You still need to do
four things:

**1. Install `jq` if it warned you it was missing.** Without it the safety
hooks fail open (warn + allow, not block). On macOS: `brew install jq`.

**2. Install the language-server binaries the doctor flagged as `MISS`** —
for languages you actually write. LSP stays inert for a language until its
binary is on PATH. Skip any language you don't use; nothing else breaks, you
just won't get LSP for it. Common installs, grouped by toolchain:

```bash
# npm-based (light, no toolchain beyond Node)
npm i -g typescript-language-server typescript pyright \
         vscode-langservers-extracted yaml-language-server \
         bash-language-server intelephense

# Toolchain-bundled (skip what you don't use)
go install golang.org/x/tools/gopls@latest                            # Go
rustup component add rust-analyzer                                    # Rust
brew install ruby && gem install ruby-lsp                             # Ruby (Homebrew Ruby, not system)
brew install --cask dotnet-sdk && dotnet tool install -g csharp-ls    # C# (needs .NET 10 SDK)
brew install kotlin-language-server                                   # Kotlin
xcode-select --install                                                # Swift + clangd (macOS)
# Java/jdtls: install a JDK + jdtls separately if you write Java.
```

**3. Start a *new* Claude Code session.** Settings, hooks, and the LSP plugin
only load at session start — nothing applies mid-session.

**4. Smoke-test it:**
- `claude plugin list` (from anywhere) — should show `jun-lsp@juns-config`, enabled.
- Start a session in a git repo: the SessionStart context block (branch, dirty status, recent commits) should appear.
- Ask Claude to `git push` — the safety hook should block it.
- Open a file in a language whose server you installed — go-to-definition should work.
- Optional schema check, from inside this repo: `claude plugin validate ./plugins/jun-lsp`.

## Re-checking your LSP binaries later

The install-time doctor only runs once. To check binary status anytime — new
project, after installing a server, on a new machine — paste this:

```bash
check() {
  if command -v "$1" >/dev/null 2>&1; then
    printf "  OK   %-15s (%s)\n" "$2" "$1"
  else
    printf "  MISS %-15s install: %s\n" "$2" "$3"
  fi
}
echo "=== LSP binary status ==="
check typescript-language-server  "TypeScript/JS"  "npm i -g typescript-language-server typescript"
check pyright-langserver          "Python"         "npm i -g pyright"
check clangd                      "C/C++"          "xcode-select --install (macOS) / LLVM"
check rust-analyzer               "Rust"           "rustup component add rust-analyzer"
check gopls                       "Go"             "go install golang.org/x/tools/gopls@latest"
check bash-language-server        "Bash"           "npm i -g bash-language-server"
check yaml-language-server        "YAML"           "npm i -g yaml-language-server"
check vscode-json-language-server "JSON"           "npm i -g vscode-langservers-extracted"
check vscode-html-language-server "HTML"           "npm i -g vscode-langservers-extracted"
check vscode-css-language-server  "CSS"            "npm i -g vscode-langservers-extracted"
check intelephense                "PHP"            "npm i -g intelephense"
check sourcekit-lsp               "Swift"          "ships with Xcode/Swift toolchain"
check ruby-lsp                    "Ruby"           "brew install ruby; gem install ruby-lsp"
check jdtls                       "Java"           "install JDK + jdtls separately"
check csharp-ls                   "C#"             "brew install --cask dotnet-sdk; dotnet tool install -g csharp-ls"
check kotlin-language-server      "Kotlin"         "brew install kotlin-language-server"
```

## Day-to-day

You don't go to `~/.claude/` or this repo folder again. Use Claude Code as
normal in your project directories — the global config applies to every
session automatically.

To update the config later: edit files in this repo, commit + push, and
re-run the `curl` install command on each machine. **The one gotcha worth
remembering:** if you change `plugins/jun-lsp/.lsp.json`, also bump the
`version` in `plugins/jun-lsp/.claude-plugin/plugin.json`. The plugin
version is pinned (no auto-update), so a `.lsp.json` change without a
version bump silently won't propagate to Claude Code's plugin cache.

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/uninstall.sh | bash
```

Restores the newest backup if one exists; otherwise removes only what this
config installed.

## What gets installed (`~/.claude/`)

| File | Purpose |
|---|---|
| `CLAUDE.md` | Global behaviour (Karpathy 4 + gstack nudges), scoped British-English rule, routing rules. ~28 lines, loads every session. |
| `settings.json` | Coarse `permissions.deny` list + wiring for the three hooks. |
| `hooks/safety-bash.sh` | PreToolUse (Bash). Hard-blocks 9 categories of dangerous command (git state, DB/migrations, destructive FS, deploy, secrets, dep-adds, mutating HTTP, system, CI). Agent blocked → you run it yourself. |
| `hooks/safety-files.sh` | PreToolUse (Write/Edit). Blocks edits to `.env*`, keys, credential files. |
| `hooks/session-context.sh` | SessionStart. Injects branch + dirty state + last 5 commits. Minimal by design. |
| `LEARNINGS.md` | Manual lesson-capture log (deliberately not a skill or auto-reflector). |
| `settings.json` `env` | `ENABLE_LSP_TOOL=1` — turns on Claude Code's native LSP, portably. |
| `jun-lsp` plugin | Self-authored unified LSP map (one `.lsp.json`). Installed via your own marketplace — zero third-party plugin code. |

## LSP layer

LSP gives Claude real symbol intelligence (go-to-definition, find-references,
diagnostics) instead of fuzzy grep. It's enabled portably via the
`ENABLE_LSP_TOOL=1` env in `settings.json`, plus a **self-authored plugin**
(`jun-lsp`) carrying one `.lsp.json` server map.

**Why a self-authored plugin (supply chain).** Custom LSP requires the plugin
mechanism. Official per-language plugins only cover ~3 languages; the rest
would mean trusting ~10 community marketplaces, each an unsandboxed
auto-update vector. Your own plugin has zero third-party plugin code, no
auto-update path (pinned `version`), and the only trust it needs — your repo
— you already extend via `curl | bash`. The language-server *binaries* are
the same supply-chain surface either way and are the irreducible risk; the
install script only **checks and reports** missing binaries, never
auto-installs them, so you control exactly what lands.

**Languages covered:** TypeScript/JS, Python, C/C++, Rust, Go, Bash, YAML,
JSON, HTML, CSS, PHP, Swift, Ruby, Java, C#, Kotlin. Each needs its language
server binary installed separately — run the install script and the LSP
doctor prints the exact command for any that are missing. Install only the
ones you actually use (LSP has no model-context cost, but each server adds a
little session-start time; the JVM ones are the heaviest).

**Adding a new language later:** add one entry to
`plugins/jun-lsp/.lsp.json` (`extensionToLanguage` is the extensibility
surface), add a matching `lsp_check` row in `install.sh`, install that
server's binary, bump the `version` in `plugin.json`. One row, no redesign.

**Manual registration fallback** (if `claude` wasn't on PATH during install):

```bash
claude plugin marketplace add Junnn888/juns-claude-config --scope user
claude plugin install jun-lsp@juns-config --scope user
```

## Prerequisites

- `git`, `bash` — required.
- `jq` — **strongly recommended.** The safety hooks parse tool input with
  `jq`. Without it they **fail open** (warn and allow, not block). Install
  `jq` or the safety layer is advisory only.

## Honest caveats (read these)

1. **`permissions.deny` is a coarse net, not the real gate.** Anthropic's own
   docs note Bash deny patterns are fragile and don't fully cover
   subprocesses (`Read(./.env)` blocks the Read tool but not `cat .env`).
   The **hooks** are the real enforcement; the deny-list is belt-and-braces.
   Verify/extend the deny rules against the current
   [permission syntax docs](https://code.claude.com/docs/en/settings) if you
   rely on them.
2. **`settings.json` is overwritten on install** (a full backup is taken
   first). If you keep custom settings, merge them back from the backup.
3. **Production-credential safety is a practice, not enforced here.** Launch
   Claude Code with only dev/local DB connection strings in its environment.
   The hooks block the *commands*; they can't verify *which database* a
   connection points at. Don't give the agent prod credentials.
4. **Some files can't be `.md`.** `settings.json` must be valid JSON and the
   hooks must be executable shell, or the system doesn't function. They're
   still plain-text and downloadable — just not Markdown.
5. **This is the lean core plus LSP, on purpose.** No skills, no
   verification hook, no auto-format — deferred until real use proves the
   need (see the design spec). LSP was the one expansion added, because it's
   a known, articulated, non-speculative need that catches a failure nothing
   else does. Add anything further only when repetition justifies it.
