---
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(gh pr create:*), Bash(gh pr view:*)
description: Generate a PR message and open a PR to the given base branch
argument-hint: "[base-branch]"
---

## Context

- Current branch: !`git branch --show-current`
- Upstream: !`git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "NONE"`
- Arguments: $ARGUMENTS

## Instructions

Generate a pull request description for the current branch, then open a PR against the base branch.

**Base branch:** if arguments were provided above, use the first word as the base branch. Otherwise default to `development`.

### Step 1 — Gather context

Run these commands to understand the changes:

1. `git merge-base <base-branch> HEAD` to find the common ancestor
2. `git log --oneline <merge-base>..HEAD` to see the commits
3. `git diff --stat <merge-base>..HEAD` for a file-level summary
4. `git diff <merge-base>..HEAD` to read the full diff

### Step 2 — Fill the template

Using the changes you gathered, fill in this template:

```
## Summary

<!-- Brief description of what this PR does and why -->

## Changes

-

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Enhancement to existing feature
- [ ] Refactoring (no functional change)
- [ ] Documentation
- [ ] CI / build configuration

## Testing

- [ ] Tested locally with `bun dev`
- [ ] Tests pass (`bun run test`)
- [ ] Tests added/updated for new business logic
- [ ] Build passes (`bun run build`)
- [ ] Lint passes (`bun run lint`)
- [ ] Verified on mobile viewport
- [ ] Verified on desktop viewport

## Screenshots

<!-- If UI changes, include before/after screenshots -->

## Notes

<!-- Any additional context, trade-offs, or follow-up items -->
```

### Rules

- **Summary:** write a concise paragraph describing what the PR does and why. Remove the HTML comment.
- **Changes:** list each meaningful change as a bullet. Group related commits into single bullets where appropriate rather than listing every commit verbatim.
- **Type of Change:** check (`[x]`) every type that applies. Uncheck the rest.
- **Testing:** check only the items that are actually relevant to the changes made. Leave irrelevant items unchecked.
- **Screenshots:** leave the HTML comment placeholder as-is unless the changes are UI-related.
- **Notes:** add any relevant context, trade-offs, or follow-up items. If there are none, leave the HTML comment placeholder.

### Step 3 — Open the PR

1. If the Upstream shown in Context is `NONE`, the branch has not been pushed. Print the filled template inside a single code fence (` ```markdown `), then ask the user to push the branch (`git push -u origin <branch>`) and re-run the command — do not attempt to push yourself.
2. If a PR already exists for this branch (`gh pr view` succeeds), print the template in a code fence and report the existing PR URL instead of creating a duplicate.
3. Otherwise create the PR, passing the filled template as the body via a heredoc:

```
gh pr create --base <base-branch> --title "<title>" --body "$(cat <<'EOF'
<filled template>
EOF
)"
```

- **Title:** a concise imperative summary of the branch's changes (not the raw branch name), prefixed by the change type. Derive the prefix from the dominant checked Type of Change:
  - New feature → `Feature: `
  - Bug fix → `Bugfix: `
  - Enhancement to existing feature → `Enhancement: `
  - Refactoring → `Refactor: `
  - Documentation → `Docs: `
  - CI / build configuration → `CI: `
  - Small corrective change that fits none of the above → `Patch: `

  If multiple types are checked, pick the one that best describes the PR's primary purpose — exactly one prefix.
- After creation, output only the PR URL — do not print the filled template.
