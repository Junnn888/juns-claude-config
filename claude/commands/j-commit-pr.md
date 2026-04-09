Generate a commit message and filled PR template from staged changes, ready to copy and paste.

## Steps

### Step 1: Check for staged changes

Run `git diff --cached --stat` to check for staged changes.

If the output is empty:

1. Run `git diff --stat` to check for unstaged changes.
2. If unstaged changes exist, report: "No staged changes found. You have unstaged changes -- stage them with `git add <files>` first." and stop.
3. If no changes at all, report: "No changes found." and stop.

Once confirmed there are staged changes:

1. Run `git diff --cached` to capture the full staged diff.
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

```
## Commit Message
```

Then a fenced code block containing the commit message.

```
## PR Body
```

Then a fenced code block (tagged as `markdown`) containing the complete filled-out template.

Do NOT run `git commit`, `git add`, `git push`, or create a PR. Only generate and display the text.
