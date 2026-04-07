Scaffold Claude Code project-specific configuration for the current working directory. This generates a tailored CLAUDE.local.md, path-scoped rules, and a settings.local.json with a typecheck hook.

## Steps

### Step 1: Discover the project

Read these files (skip any that don't exist):
- `package.json` (tech stack, scripts, dependencies)
- `tsconfig.json` or `tsconfig.app.json` (TypeScript config)
- `.eslintrc.*` or `eslint.config.*` (linting setup)
- `Makefile`, `Taskfile.yml`, or `justfile` (build commands)
- `.cursorrules` or `AGENTS.md` (existing AI agent config to migrate from)

Run `ls` on the project root and key directories (`src/`, `app/`, `lib/`, `components/`, `tests/`, `test/`) to understand directory structure.

Check which package manager is used: look for `bun.lock`, `pnpm-lock.yaml`, `yarn.lock`, or `package-lock.json`.

Check what test runner is used: look for vitest, jest, pytest, go test, etc. in package.json scripts or config files.

### Step 2: Generate CLAUDE.local.md

Create `CLAUDE.local.md` in the project root with **30-50 lines max**. Include ONLY:

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

### Step 3: Generate .claude/rules/ files

Create `.claude/rules/` directory. For each major area of the codebase, create a path-scoped rule file with a YAML frontmatter `globs` field.

Common patterns to look for:
- **Database/ORM layer**: Migration conventions, schema patterns, query client usage
- **API routes/controllers**: Auth boilerplate, response patterns, error handling
- **Components/UI**: Component structure, styling patterns, state management
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

Display what was created:

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
