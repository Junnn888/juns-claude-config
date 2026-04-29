Generate a commit message and filled PR template from staged changes, ready to copy and paste. Optionally accepts a base branch argument (e.g., "compare against development/auth-refactor") to override auto-detection.

## Steps

### Step 1: Check for staged changes

Run `git diff --cached --stat` to check for staged changes.

If the output is empty:

1. Run `git diff --stat` to check for unstaged changes.
2. If unstaged changes exist, report: "No staged changes found. You have unstaged changes -- stage them with `git add <files>` first." and stop.
3. If no changes at all, detect the base branch and diff against it:
   1. Detect the base branch (first match wins):
      a. If the user specified a branch (e.g., "compare against <branch>"), use that as the base.
      b. Run `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` and strip the `refs/remotes/origin/` prefix. If it returns a valid branch name, use that as the base.
      c. Probe common names in order: `main`, `master`, `dev`, `develop`, `development`. For each, run `git rev-parse --verify <name> 2>/dev/null`. Use the first one that exists.
      d. If nothing matches (e.g., single-branch repo with no remote), fall back: set base to `HEAD~1`.
   2. Run `git diff <base>...HEAD` (three-dot merge-base diff) to capture the branch diff.
   3. Run `git log <base>..HEAD --oneline` to list the branch commits.
   4. Report: "No uncommitted changes found. Using branch diff against `<base>` (<N> commits)."
   5. Continue to Step 2 using this diff. Mark this as **post-commit mode**.

Once confirmed there are staged changes (or falling back to last commit):

1. Run `git diff --cached` (or `git diff <base>...HEAD` in post-commit mode) to capture the full diff.
2. Run `git log --oneline -5` to see recent commit message style.

### Step 2: Search for a PR template in the project

Use the Glob tool to search for PR template files. Check these patterns in order, stopping at the first match:

1. `.github/pull_request_template.md`
2. `.github/PULL_REQUEST_TEMPLATE.md`
3. `.github/pr_template.md`
4. `.github/PR_TEMPLATE.md`
5. `.github/PULL_REQUEST_TEMPLATE/*.md` (take the first file found)
6. `pull_request_template.md` (project root)
7. `PULL_REQUEST_TEMPLATE.md` (project root)

Also check variants without the `.md` extension for each of the above.

If a template file is found, read its content.

If no template is found anywhere, use this default template:

```markdown
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

### Step 3: Generate the commit message

Based on the staged diff and recent commit history, write a commit message:

- First line: imperative mood, under 72 characters, no trailing period
- Match the tone and style of the recent commits from `git log`
- If the change is complex (multiple concerns), add a blank line followed by a body paragraph wrapped at 72 characters
- Do not include `Co-Authored-By` lines

### Step 4: Fill out the PR template

Fill in the template content while preserving ALL original markdown exactly as-is. Do not remove or rewrite any lines. Only add content.

Rules for each section:

- **Headings** (`##`): Keep unchanged.
- **HTML comments** (`<!-- ... -->`): Keep every comment exactly as-is. Write new content on the line after the comment, never inside it.
- **Summary**: Write 1-2 sentences describing what the changes do and why.
- **Changes**: Add a bullet point for each logical change under the existing `- ` marker.
- **Type of Change**: Check the appropriate boxes by replacing `- [ ]` with `- [x]`. Leave inapplicable types as `- [ ]`. Multiple types can be checked if the change spans categories.
- **Testing**: Leave ALL testing checkboxes unchecked (`- [ ]`). You cannot verify these.
- **Screenshots**: Leave the existing comment as-is. If the diff touches UI or component files, add on the next line: `UI files were changed -- consider adding screenshots before submitting.`
- **Notes**: Add relevant context about trade-offs, follow-up items, or limitations. If nothing noteworthy, leave the existing comment as-is.

If the diff is very large (50+ files), summarize at a high level rather than listing every individual file change.

### Step 5: Output the results

Display the results in this exact format:

If in **post-commit mode**, add a note at the top: "Based on last commit `<short hash>`. Commit message below is a suggested rewrite."

```
## Commit Message
```

Then a fenced code block containing the commit message.

```
## PR Body
```

Then a fenced code block (tagged as `markdown`) containing the complete filled-out template.

Do NOT run `git commit`, `git add`, `git push`, or create a PR. Only generate and display the text.
