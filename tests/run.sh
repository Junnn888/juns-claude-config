#!/usr/bin/env bash
# Runs every hook test. No dependencies beyond bash, git and node.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "$ROOT/tests/hooks/quality-gate.test.sh"
node --test "$ROOT/tests/hooks/"*.test.mjs
