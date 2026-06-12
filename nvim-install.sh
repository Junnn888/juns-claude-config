#!/usr/bin/env bash
# Installs Jun's Neovim config into ~/.config/nvim.
# Usage:  curl -fsSL <raw-url>/nvim-install.sh | bash
#
# Prerequisites: git, nvim. Plugin builds (treesitter) also need a C
# compiler on PATH (cc) — see check below.

set -euo pipefail

# --- CONFIRM THIS before publishing ------------------------------------
REPO_URL="https://github.com/Junnn888/juns-claude-config.git"
BRANCH="main"
# -----------------------------------------------------------------------

NVIM_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

command -v nvim >/dev/null 2>&1 || {
  echo "ERROR: nvim not on PATH. Install it first:" >&2
  echo "  macOS:  brew install neovim" >&2
  echo "  Debian: sudo apt install neovim" >&2
  exit 1
}
command -v cc >/dev/null 2>&1 || \
  echo "WARNING: no C compiler (cc) on PATH — treesitter parser builds will fail."

echo "==> Cloning $REPO_URL"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/repo" >/dev/null 2>&1

SRC="$TMP/repo/nvim"
[ -d "$SRC" ] || { echo "ERROR: nvim/ not found in repo. Aborting." >&2; exit 1; }

# Backup existing config wholesale.
if [ -d "$NVIM_DIR" ]; then
  BACKUP="$NVIM_DIR.backup.$TS"
  cp -a "$NVIM_DIR" "$BACKUP"
  echo "==> Backed up existing nvim config -> $BACKUP"
fi

mkdir -p "$NVIM_DIR"

echo "==> Installing init.lua + lazy-lock.json"
cp "$SRC/init.lua" "$NVIM_DIR/init.lua"
cp "$SRC/lazy-lock.json" "$NVIM_DIR/lazy-lock.json"

# First headless start bootstraps lazy.nvim; restore then pins every plugin
# to the lock-file commits so all machines run identical versions.
echo "==> Restoring plugins to lock-file versions (headless)"
nvim --headless "+Lazy! restore" +qa

echo ""
echo "Done. Installed to $NVIM_DIR"
echo "  - init.lua             editor options + lazy.nvim + plugins"
echo "  - lazy-lock.json       pinned plugin commits (Lazy restore)"
echo "Treesitter parsers compile on first launch via :TSUpdate."
