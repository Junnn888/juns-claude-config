---
description: Write a PR description for the current branch and open the PR against the given base branch
argument-hint: "[base-branch]"
disable-model-invocation: true
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(gh pr create:*), Bash(gh pr view:*)
---

Current branch: !`git branch --show-current`
Upstream: !`git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo NONE`
Arguments: $ARGUMENTS

Write a pull request description for the current branch and open the PR.
Running this command is the user's go to open it. This command is yours to run
yourself: it reads the branch and changes no file.

The base branch is the first word of the arguments. With no argument, ask the
user which base and wait, because a PR against the wrong base shows the wrong
diff.

## 1. Read the branch

1. `git merge-base <base> HEAD`
2. `git log --oneline --reverse <merge-base>..HEAD`
3. `git diff --stat <merge-base>..HEAD`
4. `git diff <merge-base>..HEAD`

## 2. Write the body

The reader is a reviewer who has not seen this work. Summary is for anyone;
Changes is for the person about to open the diff. Use plain words and short
sentences, and describe behaviour, because the diff already lists the files.

| Section | What goes in it |
|---|---|
| Summary | Three labelled lines. Problem: what is wrong or missing today, as a person using the product sees it, at most two sentences. Intent: what is true once this merges, one line. Solution: how the change gets there, at most two sentences. |
| Changes | Three to six bullets, one per behaviour, one sentence each. Visible changes first. Name a file or symbol only where the reader has to go there. |
| Commits | One line per commit from the log, oldest first: the short hash and what that commit does, at most twelve words. |
| Type of Change | The six checkboxes, with every type that applies ticked. |
| Tests | At most four bullets saying what each group of tests pins down, or "No tests changed" with a short reason. |
| Notes | At most three one-line bullets: known limits, trade-offs, follow-ups. "None" when there are none. |

Keep the body to at most 200 words, not counting the checkboxes and the
Commits list. The body ends at Notes and the title and body name no tool or
assistant, because the PR goes out as the user's own work.

Match this example for length and plainness; the content comes from the branch.

<example>
## Summary

**Problem:** Exporting the orders list ignored the active filters, so users got every order instead of the ones on screen.
**Intent:** The export holds exactly the rows the user is looking at.
**Solution:** The export takes the same filter object as the list and runs the same query.

## Changes

- The CSV export respects the status and date filters.
- An empty result exports a header row instead of failing.
- The list and the export share one query builder, so they cannot drift apart.

## Commits

- `a1b2c3d` Pass the list's filters into the export query
- `d4e5f6a` Return a header-only file for an empty result
- `0f9e8d7` Add export tests for filtered and empty results

## Type of Change

- [x] Bug fix
- [ ] New feature
- [ ] Enhancement to existing feature
- [ ] Refactoring (no functional change)
- [ ] Documentation
- [ ] CI / build configuration

## Tests

- Filtered exports contain only matching orders.
- An empty filter result gives a header row only.

## Notes

- Exports over 10,000 rows are still built in memory.
</example>

If the repo has its own template (`.github/pull_request_template.md`, or a
single file under `.github/PULL_REQUEST_TEMPLATE/`), fill that one instead,
because the repo's reviewers expect it. Apply the limits above to the sections
that match, give its other sections one line or their checkboxes, and add the
Commits section after its list of changes. A section made of checkboxes, such
as a Testing checklist, gets its ticked checkboxes and nothing after them,
because a list added below the checkboxes breaks how the section renders.

## 3. Open the PR

The title is a short imperative summary of the change with one prefix, taken
from the main ticked type: `Feature: ` (new feature), `Bugfix: ` (bug fix),
`Enhancement: ` (enhancement), `Refactor: ` (refactoring), `Docs: `
(documentation), `CI: ` (CI or build), or `Patch: ` for a small correction
that fits none of these.

- Upstream is `NONE`: the branch is not on the remote yet. Print the title and
  the body in one fenced `markdown` block and ask the user to run
  `git push -u origin <branch>` and then this command again. Pushing is the
  user's step.
- The remote branch is behind (`git rev-parse HEAD @{u}` prints two different
  hashes): a PR opened now would miss commits the body describes. Print the
  title and body the same way and ask the user to push first.
- A PR already exists for the branch (`gh pr view` succeeds): print the body in
  a fenced block and give the existing PR's URL.
- Otherwise create it, and reply with the PR URL only:

```
gh pr create --base <base> --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```
