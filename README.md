# juns-claude-config

A lean, portable Claude Code config. One curl on a fresh machine installs a
provenance-traced global `CLAUDE.md`, a deny-list + safety hooks, a manual
learnings log, and official LSP plugins. Designed from Anthropic's
official guidance and critically evaluated against (not copied from) gstack.

Philosophy: **few things, each one justified.** Every component had to catch
a failure nothing else does, or it wasn't built. That's why this is small.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/install.sh | bash
```

Backs up any existing `~/.claude` to `~/.claude.backup.<timestamp>` first.

## After install

The install script handled the file copies, hook setup, pre-installed the
official LSP plugins, and ran the binary doctor (which printed any missing
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
npm i -g typescript-language-server typescript pyright intelephense

# Toolchain-bundled (skip what you don't use)
go install golang.org/x/tools/gopls@latest                            # Go
rustup component add rust-analyzer                                    # Rust
brew install ruby && gem install ruby-lsp                             # Ruby (Homebrew Ruby, not system)
brew install --cask dotnet-sdk && dotnet tool install -g csharp-ls    # C# (needs .NET 10 SDK)
brew install lua-language-server                                      # Lua
xcode-select --install                                                # Swift + clangd (macOS)
# Kotlin: install JetBrains kotlin-lsp (github.com/Kotlin/kotlin-lsp).
# Java/jdtls: install a JDK + jdtls separately if you write Java.
```

**3. Start a *new* Claude Code session.** Settings, hooks, and the LSP plugins
only load at session start — nothing applies mid-session.

**4. Smoke-test it:**
- `claude plugin list` (from anywhere) — should show the official LSP plugins (e.g. `typescript-lsp@claude-plugins-official`), enabled.
- Start a session in a git repo: the SessionStart context block (branch, dirty status, recent commits) should appear.
- Ask Claude to `git push` — the safety hook should block it.
- Open a file in a language whose server you installed — go-to-definition should work.

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
check intelephense                "PHP"            "npm i -g intelephense"
check sourcekit-lsp               "Swift"          "ships with Xcode/Swift toolchain"
check ruby-lsp                    "Ruby"           "brew install ruby; gem install ruby-lsp"
check jdtls                       "Java"           "install JDK + jdtls separately"
check csharp-ls                   "C#"             "brew install --cask dotnet-sdk; dotnet tool install -g csharp-ls"
check kotlin-lsp                  "Kotlin"         "JetBrains kotlin-lsp (github.com/Kotlin/kotlin-lsp)"
check lua-language-server         "Lua"            "brew install lua-language-server"
```

## Neovim config (optional)

The repo also carries a minimal Neovim setup (`nvim/`) for nicer Markdown
viewing: lazy.nvim, treesitter, and render-markdown.nvim, with plugin
versions pinned in `lazy-lock.json` so every machine runs identical commits.

```bash
curl -fsSL https://raw.githubusercontent.com/Junnn888/juns-claude-config/main/nvim-install.sh | bash
```

Requires `nvim` on PATH (the script prints install hints if missing) and a C
compiler for the treesitter parser builds. Backs up any existing
`~/.config/nvim` to `~/.config/nvim.backup.<timestamp>`, copies in
`init.lua` + `lazy-lock.json`, then restores plugins headlessly to the
pinned versions.

When you change the nvim config locally, re-copy `init.lua` and
`lazy-lock.json` into `nvim/` and commit — otherwise the script installs
stale versions on the next machine.

## Day-to-day

You don't go to `~/.claude/` or this repo folder again. Use Claude Code as
normal in your project directories — the global config applies to every
session automatically.

To update the config later: edit files in this repo, commit + push, and
re-run the `curl` install command on each machine. The official LSP plugins
auto-update themselves on Claude Code start — nothing to version-bump.

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
| `settings.json` | Coarse `permissions.deny` list + wiring for the three hooks + status-line wiring + enabled plugins. |
| `statusLine.sh` | Status line showing model · token count · context-window %. Needs `jq`; prints nothing without it. |
| `hooks/safety-bash.sh` | PreToolUse (Bash). Hard-blocks 9 categories of dangerous command (git state, DB/migrations, destructive FS, deploy, secrets, dep-adds, mutating HTTP, system, CI). Agent blocked → you run it yourself. |
| `hooks/safety-files.sh` | PreToolUse (Write/Edit). Blocks edits to `.env*`, keys, credential files. |
| `hooks/session-context.sh` | SessionStart. Injects branch + dirty state + last 5 commits. Minimal by design. |
| `settings.json` → PreToolUse(`ExitPlanMode`) | Inline **prompt hook** (Sonnet, not a `.sh` file). At plan-exit it blocks a code plan unless each of the five axes — simplicity, over-engineering, logic, UX, performance — carries a falsifiable note; the deny reason is fed back so Claude revises. Pairs with the CLAUDE.md *Coding-plan assessment* rubric. |
| `LEARNINGS.md` | Manual lesson-capture log (deliberately not a skill or auto-reflector). |
| `mcp.json` | Tolaria MCP server. Only installed when `/Applications/Tolaria.app` exists, and never overwrites an existing `mcp.json`. |

## LSP layer

LSP gives Claude real symbol intelligence (go-to-definition, find-references,
diagnostics) instead of fuzzy grep. It's provided by Anthropic's **official,
first-party LSP plugins** from the `claude-plugins-official` marketplace.
Installing one of these plugins auto-enables Claude Code's built-in LSP tool —
no env var, no self-authored plugin, no third-party marketplace.

**Why official plugins (supply chain).** Anthropic now ships first-party LSP
plugins covering 12 languages, so there's nothing to self-author and no
community marketplace to trust. `claude-plugins-official` is auto-registered
on every fresh Claude Code start; the install script just pre-installs the 12
plugins (no `marketplace add` needed). The language-server *binaries* remain
the irreducible supply-chain surface, so the install script only **checks and
reports** missing binaries — never auto-installs them — so you control exactly
what lands.

**Languages covered (12):** TypeScript/JS, Python, C/C++, Rust, Go, PHP,
Swift, Java, C#, Kotlin, Lua, Ruby. Bash, YAML, JSON, HTML and CSS are **not**
covered — the official marketplace has no LSP plugin for them (low payoff:
they have no cross-file symbol graph to navigate). Each language needs its
server binary installed separately — the LSP doctor prints the exact command
for any that are missing. Install only the ones you actually use (LSP has no
model-context cost, but each server adds a little session-start time; the JVM
ones are the heaviest).

**Adding a new language later:** install the official plugin
(`claude plugin install <name>-lsp@claude-plugins-official --scope user`), add
the plugin name to the `LSP_PLUGINS` array (and a `lsp_check` row) in
`install.sh` plus the README doctor snippet, then install that server's binary.

**Manual install fallback** (if `claude` wasn't on PATH during install):

```bash
for p in typescript-lsp pyright-lsp clangd-lsp rust-analyzer-lsp gopls-lsp \
         php-lsp swift-lsp jdtls-lsp csharp-lsp kotlin-lsp lua-lsp ruby-lsp; do
  claude plugin install "$p@claude-plugins-official" --scope user
done
```

The install also enables three non-LSP official plugins — `frontend-design`,
`code-simplifier` and `coderabbit` (declared in `settings.json` and
pre-installed by the script).

## Prerequisites

- `git`, `bash` — required.
- `jq` — **strongly recommended.** The safety hooks parse tool input with
  `jq`, and the status line renders with it. Without `jq` the hooks **fail
  open** (warn and allow, not block) and the status line prints nothing.

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
5. **This is the lean core plus LSP, on purpose.** No skills, no auto-format —
   deferred until real use proves the need (see the design spec). The two
   expansions added are LSP and the plan-reviewer prompt hook (PreToolUse on
   `ExitPlanMode`), each a known, articulated, non-speculative need that
   catches a failure nothing else does. Add anything further only when
   repetition justifies it.
