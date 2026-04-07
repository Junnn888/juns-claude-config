# Global Workflow Preferences

## Approach
- Think step-by-step through problems before writing code.
- For tasks involving 3+ files or architectural decisions, start with a plan before making edits.
- Always read existing files before modifying them. Understand the current implementation.
- Prefer editing existing files over creating new ones.
- When exploring unfamiliar code, trace the full path: caller -> function -> side effects.

## Communication
- Be direct and concise. State what you did and why.
- When a task is ambiguous, state your assumptions before proceeding.
- Skip pleasantries.
- No emojis in code, commits, or technical explanations.

## Code Quality
- Follow existing patterns and conventions in the codebase.
- Do not add comments that restate what the code does.
- When fixing bugs, understand the root cause before applying a fix.
- Run existing tests/linters when available before declaring work complete.

## Git
- Do NOT run git commit, git add, or git push unless explicitly asked.
- Read-only git commands (status, diff, log, blame, show) are fine.
