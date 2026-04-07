Analyze recent commits on the current branch and extract coding patterns into `.claude/rules/patterns.md`. Patterns committed to the codebase are treated as approved ("Prefer"); patterns replaced by commits are treated as anti-patterns ("Avoid").

## Steps

### Step 1: Determine analysis range

Read `.claude/rules/patterns.md` if it exists. Look for the HTML comment `<!-- Last analyzed: <sha> ... -->` to find the last analyzed commit SHA.

- **If file exists with SHA:** analyze commits from that SHA to HEAD
- **If file exists without SHA:** analyze the last 20 commits on the current branch
- **If file doesn't exist:** analyze the last 20 commits on the current branch

Run `git log <range> --oneline` to list commits to analyze. If there are no new commits, report "No new commits to analyze" and stop.

### Step 2: Analyze diffs

For each commit (or as a batch if under 30 commits), run `git diff <start-sha>..<end-sha>` to see what changed.

For each meaningful change, identify:
- **What the code changed TO** → candidate "Prefer" pattern
- **What the code changed FROM** → candidate "Avoid" pattern

**Skip these — they are not patterns:**
- Whitespace/formatting changes
- Import reordering
- Version bumps and dependency updates
- Auto-generated files (lockfiles, .d.ts, migrations with timestamps)
- One-off bug fixes (null checks, off-by-one fixes)
- Feature-specific business logic
- Config/env changes
- Comment additions or removals

**Keep these — they ARE patterns:**
- API usage changes (which client, wrapper, or utility to use)
- Module/export structure (named vs default, barrel files, re-exports)
- Error handling approach (error types, try/catch style, Result patterns)
- State management patterns (hooks, stores, context usage)
- Type patterns (interface vs type, enum vs const object, generics usage)
- Testing patterns (what to mock, assertion style, test structure)
- Component patterns (composition, prop patterns, styling approach)
- Data fetching patterns (SWR, React Query, server actions, loaders)
- File/folder organization choices

### Step 3: Filter and consolidate

From the candidates identified in Step 2:

1. **Discard weak signals** — a pattern must represent a deliberate choice, not an incidental side effect of a feature. If a change only appears once and could be coincidental, skip it.

2. **Consolidate similar patterns** — if multiple commits reinforce the same preference (e.g., three commits all switch from `interface` to `type`), merge into one entry.

3. **Check for contradictions** — if a new "Prefer" pattern contradicts an existing "Avoid" (or vice versa), the newer commit wins. Update the existing entry.

4. **Make entries actionable** — each entry must be specific enough to follow. Bad: "use good error handling". Good: "use `AppError` class with error codes instead of throwing raw `Error`".

### Step 4: Merge with existing patterns

If `.claude/rules/patterns.md` already exists:
- Read all existing Prefer and Avoid entries
- Add new entries, deduplicating against existing ones
- If an existing pattern is reinforced by a new commit, update its commit reference
- If an existing pattern is contradicted, replace it
- **Cap at 15 Prefer + 15 Avoid entries.** If at capacity, consolidate related patterns into broader rules rather than dropping entries.

### Step 5: Write patterns file

Write `.claude/rules/patterns.md` with this exact structure:

```markdown
---
globs: ["**/*"]
---

# Learned Patterns
<!-- Last analyzed: {HEAD_SHA} ({TODAY_DATE}) -->

## Prefer
- {pattern description} ({commit_sha_short}, {commit_date})
- ...

## Avoid
- {pattern description} — {what to do instead} ({commit_sha_short})
- ...
```

Rules:
- Use the short SHA (7 chars) and date (YYYY-MM-DD) for each entry
- Each Avoid entry should reference what to do instead
- Keep the total file under 50 lines
- Ensure the YAML frontmatter has `globs: ["**/*"]`
- The HTML comment with the last analyzed SHA must be on its own line after the heading

### Step 6: Report

Display what was learned:

```
Analyzed N commits ({start_sha}..{end_sha})

New patterns found:
  + Prefer: {description}
  - Avoid: {description}

Updated: .claude/rules/patterns.md ({X} prefer, {Y} avoid total)
```

If no patterns were found in the analyzed commits, report:

```
Analyzed N commits ({start_sha}..{end_sha})

No new patterns detected. Changes were feature-specific or non-pattern.

.claude/rules/patterns.md unchanged.
```
