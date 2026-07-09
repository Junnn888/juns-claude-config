#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Hard-blocks dangerous commands.
# Mechanic: exit 2 = block + stderr fed back to Claude. exit 0 = allow.
# Design: agent is blocked; the USER re-runs the command manually outside
# the agent. Tiers collapsed to messaging only (all categories hard-block).
# Must stay <200ms (pure regex). Runs unsandboxed — keep it simple.

set -euo pipefail

input="$(cat)"

# Extract the bash command. Prefer jq; degrade gracefully if absent.
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
else
  # jq missing: cannot reliably parse. Fail OPEN (exit 0) so the agent
  # stays usable, and warn. Install jq for this hook to enforce.
  echo "safety-bash: jq not found — command not screened. Install jq to enable enforcement." >&2
  exit 0
fi

[ -z "$cmd" ] && exit 0

block() {
  # $1 = category, $2 = why
  echo "BLOCKED ($1): $2" >&2
  echo "This is the user's manual step. Do NOT retry or work around it." >&2
  echo "Surface the exact command so the user can run it themselves outside the agent." >&2
  exit 2
}

lc="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

# quoted text is data, not commands; a command runs at start-of-string or after
# ; & | ( — optionally preceded by VAR=val assignments; dash-flags (with an
# optional value argument, e.g. -C <path>) may sit between git and its subcommand
stripped="$(printf '%s' "$lc" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g")"
CMD_POS='(^|[;&|(])[[:space:]]*([a-z_][a-z0-9_]*=[^[:space:]]*[[:space:]]+)*'
GIT_FLAGS='([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*'

# 1. Version control
echo "$stripped" | grep -Eq "${CMD_POS}git${GIT_FLAGS}[[:space:]]+(commit|add|push|reset|rebase|clean)([[:space:]]|\$)" \
  && block "version-control" "git state changes are the user's call"
echo "$lc" | grep -Eq 'git[[:space:]]+push.*(--force|-f)([[:space:]]|$)' \
  && block "version-control" "force-push is destructive and user-only"
echo "$lc" | grep -Eq 'git[[:space:]]+(checkout|restore)[[:space:]]+(\.|--)' \
  && block "version-control" "discarding working-tree changes is user-only"

# 2. DB / migrations
echo "$lc" | grep -Eq 'supabase[[:space:]]+db[[:space:]]+(push|reset)' \
  && block "db-migration" "DB push/reset is user-only"
echo "$lc" | grep -Eq 'prisma[[:space:]]+migrate[[:space:]]+(deploy|reset)' \
  && block "db-migration" "migration deploy/reset is user-only"
echo "$lc" | grep -Eq 'drizzle-kit[[:space:]]+push' \
  && block "db-migration" "drizzle-kit push is user-only"
echo "$lc" | grep -Eq '(^|[;&| ])psql([[:space:]]|$)' \
  && block "db-migration" "direct psql access is user-only"
echo "$lc" | grep -Eq '(drop[[:space:]]+(table|database)|truncate[[:space:]]+table|delete[[:space:]]+from)' \
  && block "db-migration" "destructive SQL is user-only"

# 3. Destructive filesystem
echo "$lc" | grep -Eq '(^|[;&| ])rm[[:space:]]+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r|-r[[:space:]]+-f|-f[[:space:]]+-r)' \
  && block "destructive-fs" "recursive force-delete is user-only"
echo "$lc" | grep -Eq 'find[[:space:]].*-delete' \
  && block "destructive-fs" "find -delete is user-only"
echo "$lc" | grep -Eq 'chmod[[:space:]]+(-r[[:space:]]+)?777|chmod[[:space:]]+777[[:space:]]+-r' \
  && block "destructive-fs" "chmod 777 -R is user-only"
echo "$lc" | grep -Eq '(^|[;&| ])(mkfs|dd[[:space:]]+if=)' \
  && block "destructive-fs" "disk-level write is user-only"

# 4. Deploy / infra
echo "$lc" | grep -Eq 'vercel.*(--prod|deploy)' \
  && block "deploy" "deploy is user-only"
echo "$lc" | grep -Eq 'terraform[[:space:]]+(apply|destroy)' \
  && block "deploy" "terraform apply/destroy is user-only"
echo "$lc" | grep -Eq 'aws[[:space:]]+(s3[[:space:]]+r[bm]|ec2[[:space:]]+terminate)' \
  && block "deploy" "destructive AWS op is user-only"
echo "$lc" | grep -Eq 'kubectl[[:space:]]+delete' \
  && block "deploy" "kubectl delete is user-only"
echo "$lc" | grep -Eq 'docker[[:space:]]+(system[[:space:]]+prune|volume[[:space:]]+rm)' \
  && block "deploy" "destructive docker op is user-only"

# 5. Secrets exposure via bash
echo "$lc" | grep -Eq '(cat|less|more|head|tail|bat)[[:space:]].*\.env([[:space:]]|$|\.)' \
  && block "secrets" "reading env files is user-only"
echo "$lc" | grep -Eq '(^|[;&| ])printenv([[:space:]]|$)' \
  && block "secrets" "dumping environment is user-only"

# 6. Dependencies — block ADDING / publishing, allow bare restore (npm ci, npm install)
echo "$lc" | grep -Eq '(npm[[:space:]]+(i|install|add)|pnpm[[:space:]]+add|yarn[[:space:]]+add)[[:space:]]+[^-[:space:]]' \
  && block "dependencies" "adding a dependency is the user's call"
echo "$lc" | grep -Eq 'pip[[:space:]]+install[[:space:]]+[^-[:space:]]' \
  && block "dependencies" "adding a Python dependency is the user's call"
echo "$lc" | grep -Eq '(npm|cargo|pnpm|yarn)[[:space:]]+publish' \
  && block "dependencies" "publishing a package is user-only"

# 7. External side effects
echo "$lc" | grep -Eq 'curl.*(-x[[:space:]]*(post|put|delete|patch)|--request[[:space:]]*(post|put|delete|patch))' \
  && block "external" "mutating HTTP request is user-only"

# 8. System
echo "$lc" | grep -Eq '(^|[;&| ])sudo([[:space:]]|$)' \
  && block "system" "sudo is user-only"
echo "$lc" | grep -Eq '>>?[[:space:]]*~?/?\.?(zshrc|bashrc|bash_profile|profile)' \
  && block "system" "editing shell rc files is user-only"
echo "$lc" | grep -Eq '(^|[;&| ])(shutdown|reboot|kill[[:space:]]+-9|killall|chsh)([[:space:]]|$)' \
  && block "system" "system control command is user-only"

# 9. CI / automation — command-position anchored on the quote-stripped string:
# the bare pattern matched "gh" as a word suffix ("high run" → "gh run")
echo "$stripped" | grep -Eq "${CMD_POS}gh[[:space:]]+(workflow[[:space:]]+run|run[[:space:]]|secret[[:space:]]|api.*-x[[:space:]]*(post|put|delete))" \
  && block "ci-automation" "CI/automation mutation is user-only"

exit 0
