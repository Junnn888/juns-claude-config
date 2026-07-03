---
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git merge-base:*)
description: Generate a PR message from branch commits
---

## Context

- Current branch: !`git branch --show-current`
- Arguments: $ARGUMENTS

## Instructions

Generate a pull request description for the current branch.

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

### Step 3 — Output

Print the filled template inside a single code fence (` ```markdown `) so the user can copy-paste the raw markdown directly into GitHub. Do not add any text outside the code fence.
