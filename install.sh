#!/usr/bin/env bash
# Installs Jun's Claude Code config into ~/.claude.
# Usage:  curl -fsSL <raw-url>/install.sh | bash
#
# Prerequisites: git, bash. Recommended: jq (the safety hooks fail OPEN
# without it — they warn and allow rather than block).

set -euo pipefail

# --- CONFIRM THIS before publishing ------------------------------------
REPO_URL="https://github.com/Junnn888/juns-claude-config.git"
BRANCH="main"
# -----------------------------------------------------------------------

CLAUDE_DIR="$HOME/.claude"
TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Cloning $REPO_URL"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/repo" >/dev/null 2>&1

SRC="$TMP/repo/claude"
[ -d "$SRC" ] || { echo "ERROR: claude/ not found in repo. Aborting." >&2; exit 1; }

# Backup existing config wholesale (Claude Code also keeps its own backups,
# but this captures hooks + CLAUDE.md too).
if [ -d "$CLAUDE_DIR" ]; then
  BACKUP="$CLAUDE_DIR.backup.$TS"
  cp -a "$CLAUDE_DIR" "$BACKUP"
  echo "==> Backed up existing ~/.claude -> $BACKUP"
fi

mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/commands"

echo "==> Installing CLAUDE.md"
cp "$SRC/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

echo "==> Installing settings.json"
echo "    NOTE: this OVERWRITES ~/.claude/settings.json (backup taken above)."
echo "    If you had custom settings, merge them back from the backup."
cp "$SRC/settings.json" "$CLAUDE_DIR/settings.json"

echo "==> Installing hooks"
cp "$SRC/hooks/"*.sh "$CLAUDE_DIR/hooks/"
chmod +x "$CLAUDE_DIR/hooks/"*.sh

echo "==> Installing commands"
cp "$SRC/commands/"*.md "$CLAUDE_DIR/commands/" 2>/dev/null || true

if [ -f "$CLAUDE_DIR/LEARNINGS.md" ]; then
  echo "==> LEARNINGS.md already exists — leaving your copy untouched."
else
  echo "==> Installing LEARNINGS.md"
  cp "$SRC/LEARNINGS.md" "$CLAUDE_DIR/LEARNINGS.md"
fi

command -v jq >/dev/null 2>&1 || \
  echo "WARNING: jq not installed. Safety hooks fail OPEN (warn+allow) until you install jq."

# --- LSP layer ---------------------------------------------------------
# LSP is provided by Anthropic's official, first-party plugins from the
# `claude-plugins-official` marketplace, which is auto-registered on every
# fresh Claude Code start (no `marketplace add` needed). Installing an
# official LSP plugin auto-enables Claude Code's built-in LSP tool.
LSP_PLUGINS=(
  typescript-lsp pyright-lsp clangd-lsp rust-analyzer-lsp gopls-lsp php-lsp
  swift-lsp jdtls-lsp csharp-lsp kotlin-lsp lua-lsp ruby-lsp
)

echo ""
echo "==> LSP: pre-installing official plugins (claude-plugins-official)"
if command -v claude >/dev/null 2>&1; then
  for p in "${LSP_PLUGINS[@]}"; do
    if claude plugin install "${p}@claude-plugins-official" --scope user >/dev/null 2>&1; then
      echo "    ok    $p"
    else
      echo "    skip  $p (already installed or unavailable)"
    fi
  done
else
  echo "    'claude' not on PATH. Install the LSP plugins manually after install:"
  echo "      for p in ${LSP_PLUGINS[*]}; do"
  echo "        claude plugin install \"\$p@claude-plugins-official\" --scope user"
  echo "      done"
fi

# LSP doctor: check-and-report only (never auto-install — the language-server
# binaries are the irreducible supply-chain surface, so you choose what lands).
# A plugin stays inert until its binary is on PATH; this prints the exact
# command for any that are missing.
echo ""
echo "==> LSP doctor (checking language-server binaries on PATH)"
lsp_check() {
  # $1 = binary, $2 = language label, $3 = install hint
  if command -v "$1" >/dev/null 2>&1; then
    echo "    ok    $2 ($1)"
  else
    echo "    MISS  $2 — install: $3"
  fi
}
lsp_check typescript-language-server "TypeScript/JS" "npm i -g typescript-language-server typescript"
lsp_check pyright-langserver        "Python"        "npm i -g pyright  (or: pip install pyright)"
lsp_check clangd                    "C/C++"         "xcode-select --install (macOS) / install LLVM"
lsp_check rust-analyzer             "Rust"          "rustup component add rust-analyzer"
lsp_check gopls                     "Go"            "go install golang.org/x/tools/gopls@latest"
lsp_check intelephense              "PHP"           "npm i -g intelephense"
lsp_check sourcekit-lsp             "Swift"         "ships with the Xcode / Swift toolchain"
lsp_check ruby-lsp                  "Ruby"          "gem install ruby-lsp"
lsp_check jdtls                     "Java"          "install Eclipse JDT LS (jdtls) + a JDK"
lsp_check csharp-ls                 "C#"            "dotnet tool install -g csharp-ls"
lsp_check kotlin-lsp                "Kotlin"        "JetBrains kotlin-lsp (github.com/Kotlin/kotlin-lsp)"
lsp_check lua-language-server       "Lua"           "brew install lua-language-server"
echo "    (MISS = optional; install only the languages you actually use.)"
# -----------------------------------------------------------------------

echo ""
echo "Done. Installed to $CLAUDE_DIR"
echo "  - CLAUDE.md            global behaviour/language/routing config"
echo "  - settings.json        permissions.deny + hook wiring"
echo "  - commands/              custom slash commands (e.g. /pr-message)"
echo "  - hooks/safety-bash.sh, safety-files.sh, session-context.sh"
echo "  - LEARNINGS.md         manual lesson-capture log"
echo "  - LSP plugins          12 official servers from claude-plugins-official"
echo "Start a new Claude Code session for changes to take effect."
