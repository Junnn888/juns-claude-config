Scaffold or update Claude Code project-specific configuration for the current working directory. This generates a tailored CLAUDE.local.md, path-scoped rules, and a settings.local.json with a typecheck hook. If config already exists, it re-evaluates the project and updates stale sections while preserving manual customizations.

## Steps

### Step 1: Discover the project

**1a. Read project source files** (skip any that don't exist):
- `package.json` (tech stack, scripts, dependencies)
- `tsconfig.json` or `tsconfig.app.json` (TypeScript config)
- `.eslintrc.*` or `eslint.config.*` (linting setup)
- `Makefile`, `Taskfile.yml`, or `justfile` (build commands)
- `.cursorrules` or `AGENTS.md` (existing AI agent config to migrate from)

Run `ls` on the project root and key directories (`src/`, `app/`, `lib/`, `components/`, `tests/`, `test/`) to understand directory structure.

Check which package manager is used: look for `bun.lock`, `pnpm-lock.yaml`, `yarn.lock`, or `package-lock.json`.

Check what test runner is used: look for vitest, jest, pytest, go test, etc. in package.json scripts or config files.

**1b. Read existing config** (skip any that don't exist):
- `CLAUDE.local.md`
- `.claude/settings.local.json`
- All files in `.claude/rules/` (excluding `patterns.md`, which is managed by `/j-learn`)

If any of these exist, this is an **update run** rather than a fresh init. Note what exists so later steps can diff against it.

### Step 2: Generate or update CLAUDE.local.md

**If CLAUDE.local.md does not exist**, create it from scratch.

**If CLAUDE.local.md already exists**, compare its content against the current project state:
- Update sections that are now stale (e.g., framework changed, package manager switched, key abstractions added or removed).
- Preserve lines that are still accurate or that represent manual additions not derivable from project files. When unsure whether a line was manually added, keep it.
- Remove lines that reference tools, frameworks, or patterns no longer present in the project.

In either case, the file should be **30-50 lines max** and include ONLY:

1. **Project identity** (2-3 lines): Name, framework, key tech. Mention anything non-obvious (e.g., "types are manually maintained" or "monorepo with turborepo").
2. **Hard rules** (5-10 lines): Things that cause real breakage if violated. Only include rules that Claude would NOT discover by reading 2-3 existing files. Examples:
   - Package manager (if not npm)
   - Export style (if enforced, e.g., named-only)
   - Type patterns (if non-standard, e.g., `as const` not `enum`)
   - Import alias (if `@/` or similar)
   - Auth patterns (if there's a wrapper function that must be used)
   - Type generation (if manual vs auto-generated)
3. **Key abstractions** (3-5 lines): Client tiers, service layers, or other architectural patterns that have multiple variants where using the wrong one causes bugs.
4. **Common commands** (1-2 lines): Build, test, lint, dev server.

**Do NOT include**: File naming conventions (discoverable), import ordering (discoverable), component structure (discoverable), CI/CD details, Prettier/formatting config (handled by pre-commit hooks), directory tree (use `ls`).

### Step 3: Generate or update .claude/rules/ files

Create `.claude/rules/` directory if it doesn't exist.

**If no rule files exist**, generate them from scratch based on the project scan.

**If rule files already exist**, compare each one against the current project state:
- **Update** rules whose globs still match existing paths but whose content is stale (e.g., the ORM changed, a new auth pattern was introduced).
- **Remove** rule files whose globs no longer match any existing paths (e.g., a `components/` rule when the project no longer has a `components/` directory).
- **Add** new rule files for areas that now exist but weren't covered before.
- **Do not touch** `patterns.md` — that file is managed by `/j-learn`.

For each major area of the codebase, create a path-scoped rule file with a YAML frontmatter `globs` field.

Common patterns to look for:
- **Database/ORM layer**: Migration conventions, schema patterns, query client usage
- **API routes/controllers**: Auth boilerplate, response patterns, error handling
- **Components/UI**: Component structure, composition patterns, state management
- **UI/Layout**: Component library preferences (e.g., shadcn over raw HTML), CSS methodology (Tailwind vs CSS modules vs styled-components), layout conventions (flex/grid, container patterns), spacing/sizing system, responsive breakpoints, theme/color usage
- **Tests**: Test runner config, fixture patterns, what to test vs not test
- **Types/Models**: Type patterns, generation strategy, sync obligations

Each file should have:
```yaml
---
globs: ["relevant/glob/pattern/**"]
---
```

Only create rules for areas that have non-obvious conventions. Skip if the area follows standard framework patterns.

### Step 4: Generate .claude/settings.local.json

Create `.claude/settings.local.json` with a PostToolUse typecheck hook tailored to the project:

- **TypeScript projects**: `{pkg_manager} run typecheck 2>&1 | tail -20` (or `npx tsc --noEmit 2>&1 | tail -20` if no typecheck script)
- **Python projects**: Consider mypy or pyright
- **Go projects**: `go vet ./... 2>&1 | tail -20`
- **No type system**: Skip the hook

Always include `| tail -20` to cap output and a 15-second timeout.

If `.claude/settings.local.json` already exists, merge the hooks section without overwriting existing permissions.

### Step 5: Update .gitignore

Add `.claude/rules/` to `.gitignore` if not already present. Do NOT add `.claude/settings.local.json` or `CLAUDE.local.md` (these are gitignored by convention).

### Step 6: Report

**Fresh init** — display what was created:

```
Project config initialized:

  CLAUDE.local.md          — [N] lines, [M] hard rules
  .claude/rules/           — [X] rule files
  .claude/settings.local.json — PostToolUse typecheck hook
  .gitignore               — updated

Rule files:
  - [filename] — [glob] — [brief description]
  - ...

Start a new session to pick up the changes.
```

**Update run** — display what changed:

```
Project config updated:

  CLAUDE.local.md          — [updated | unchanged]
  .claude/settings.local.json — [updated | unchanged]

  Rules added:    [list new files, or "none"]
  Rules updated:  [list updated files, or "none"]
  Rules removed:  [list removed files, or "none"]
  Rules unchanged: [list untouched files, or "none"]

Start a new session to pick up the changes.
```
