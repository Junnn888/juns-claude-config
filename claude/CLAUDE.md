# Global Workflow Preferences

## Approach
- Think step-by-step through problems before writing code.
- For tasks involving 3+ files or architectural decisions, start with a plan before making edits.
- Always read existing files before modifying them. Understand the current implementation.
- Prefer editing existing files over creating new ones.
- When exploring unfamiliar code, trace the full path: caller -> function -> side effects.

## Discovery
- Three tiers, default to cheapest: Grep/Glob (pattern locations/counts) → Read (understand 1-3 known files) → Agent/Task (cross-file comprehension or unknown starting point).
- Escalate when the current tier stops yielding new information, not before.
- Grep refinement is fine (2-3 queries narrowing scope). Grep thrashing is not (5+ queries, no new information — escalate to Read or Agent).

## Skills

Invoke skills automatically when the user's request matches — do not wait for a slash command.

**Auto-invoke:**
- `/j-search` — User asks about the codebase: "how does X work?", "where is X?", "what calls X?". Use only for questions requiring cross-file understanding; for simple lookups (specific file, function name), use Grep/Glob per the Discovery tier.
- `/j-debug` — User reports a bug, error, or unexpected behavior; provides stack traces or error messages.
- `/j-plan` — Task involves 3+ files or architectural decisions; user says "plan this", "how should I approach".
- `/j-review` — After completing multi-file implementation work; user says "review this", "check my changes".
- `/j-commit-pr` — User asks to commit, create a PR, or generate a commit message from staged changes.
- `/j-learn` — After a batch of commits establishes patterns; user says "learn patterns".

**On request only** (invoke only when explicitly asked):
- `/j-init`, `/j-update`, `/j-am`, `/j-block-agent-commits`

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

## Simplicity
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

## Surgical Changes
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- If you notice unrelated dead code, mention it — don't delete it.
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.
- Every changed line should trace directly to the user's request.

## Git
- Do NOT run git commit, git add, or git push unless explicitly asked.
- Read-only git commands (status, diff, log, blame, show) are fine.

## Agents
- After completing implementation work that touches 3+ files, use `/j-review` before reporting work as done. Report findings alongside completion.
- When asked to debug a problem that spans multiple modules, read `~/.claude/agents/debugger.md` and spawn a diagnostic agent first. Apply fixes based on its findings.
- When starting a new feature, offer test-first development: spawn `@test-writer` with the feature spec to create failing tests, then implement to pass them.
