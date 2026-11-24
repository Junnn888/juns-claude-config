---
description: "Review the current branch against a base ref: CodeRabbit, the review agent and the weakened-checks scan report; the main session weighs the findings and sends the fixes out; /simplify then reports on the result; a final re-check, a refute pass on what is left to decide, and a report follow"
argument-hint: "<base ref>"
disable-model-invocation: true
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git merge-base:*), Bash(git status:*), Bash(shasum:*), Bash(python3 ~/.claude/scripts/gate-scan.py:*)
---

Base ref: $ARGUMENTS
Current branch: !`git branch --show-current`

Review this branch's change against the base ref. With no base ref, ask the
user which ref and wait, because a review against the wrong base reports other
people's changes. Start with `git merge-base <base> HEAD`: every reviewer
compares from that commit to the working tree, so uncommitted and untracked
changes are part of the review.

Running this command is the user's go for the fixes in steps 3 and 5. The
reviewers only report. You weigh what they found, and the fixes go out to
`patch` or `builder`.

## 1. The reviewers report

Start all three in one message.

- **CodeRabbit**: the `coderabbit:code-reviewer` agent, model sonnet, effort
  high. Ask it to review the diff from the merge-base to the working tree and
  return every finding (file and line, severity, the claim, a failing case,
  the fix it suggests) with the number of findings its tool reported, so you
  can see that none was dropped. If the agent is not installed or does not
  finish, record CodeRabbit as "not run" with the reason and carry on.
- **The `review` agent**: give it the merge-base, the files the branch changed
  (`git diff --name-only <merge-base>` plus the untracked files in
  `git status --short`) and the repo's check commands. Ask it for one more
  list, kept apart from its findings and needing no failing case: the comments
  the change adds that only restate the code.
- **The scan**: `python3 ~/.claude/scripts/gate-scan.py <base>`. It tags lines
  that weaken a check and does not judge them: RH-1 a test removed or skipped,
  RH-3 a snapshot changed without its owner, RH-4 a placeholder in product
  code, RH-12 code that behaves differently under test or CI, RH-13 a lint or
  type suppression, RH-14 a CI or hook bypass, RH-15 a relaxed threshold or
  timeout, RH-16 a swallowed exception. Exit code 2 or a `GATE_ERROR` line
  means the scan did not run: report it as "unavailable" with the reason,
  since "none" would claim a clean result that nobody produced.

## 2. Weigh the findings together

Group the findings by cause, so that one cause reported twice is fixed once.
Each finding is a claim: check it against the current code before it earns a
fix, with one Explore batch for what the reports do not already quote, and
name the ones you drop and why. Then sort what is left:

- **Fix now**: a problem in the branch's own change with one clear fix that
  stays inside the finding. A bug with a concrete failing case, a comment that
  restates the code, and a test the scan shows was removed by accident all
  belong here.
- **Yours to decide**: a problem in the branch's own change where the fix is a
  choice: it changes behaviour, widens the branch, or has more than one
  reasonable shape. Missing tests and scale problems that need more than a
  small fix belong here. So does every other line the scan tagged, with one
  sentence on what the line does: it silences a failure, or something visible
  in this diff justifies it.
- **Later**: findings about code the branch did not change, cosmetic points,
  and findings the refute pass in step 7 cuts.

## 3. Fix

Send one writer per cause, routed as the style describes. Each hand-over also
quotes the finding word for word and limits the files to those the branch
changed and the tests beside them.

## 4. Simplify reports

Record a checksum of each file the branch changed (`shasum <files>`), then run
the built-in `/simplify` skill on the branch's change with this request:
report each finding with its file and line and the change it would make, and
leave every file as it is, because this command decides which changes are
made. Start each review pass `/simplify` asks for as an Explore agent with
model sonnet and effort high. These passes suggest tidy-ups that you check
before any fix goes out, so they do not need the `review` agent: it runs on
Fable, and Fable is kept for the bug hunt in step 1 and the refute pass in
step 7. Take the checksums again
afterwards. If one differs, `/simplify` edited that file: name it in the
report so the user knows which lines came from it.

## 5. Weigh what simplify found

Over-built code is this step's subject. Send out the findings that hold and
stay inside the branch's change, the same way as step 3. The rest go to Later.

## 6. Final re-check

Run the repo's own checks (type check, lint, tests, as its instructions or
package scripts name them); a check the repo does not define is "not run". Run
the scan again, and CodeRabbit once more from the same merge-base. Report a
failing check with its last 15 lines and leave it for the user, because a
second round of fixes here would hide how far the branch moved during review.
A line the scan tags now and did not tag in step 1 came from a fix: say so. A
finding CodeRabbit reports now and did not report in step 1 goes under Yours
to decide, marked as found after the fixes.

## 7. Refute what is left to decide

If findings sit under Yours to decide, send them word for word to one
`refute` agent with the merge-base and the files they name, and nothing else:
no verdicts from step 2 and no cut rules of your own, so it judges by its own
definition rather than by your reading. Leave the scan's
lines out: they have no failing case to test, so they stay under Yours to
decide as they are. A finding `refute` cuts moves to Later, with its reason as
the `If left:` line. A finding it keeps goes into the report with its narrowed
options and its recommendation. With nothing to decide, skip this step.

## 8. Report

Open with `Fixed <n> · To decide <n> · Later <n>`, then three sections:

1. **Done: read, then commit.** One line per fix.
2. **Yours to decide before commit.** Each item gives the problem, what the
   user would see, the options, and a one-line recommendation. A scan item
   uses what its tag means, in words, with path:line as the title, and has the
   options restore, keep, or leave open.
3. **Later.** One line per item, ending `If left:` and what happens.

<example>
**Export times out on large accounts** (app/orders/export.ts:41)
Problem: the export builds the whole file in memory.
What you'd see: the largest customers' exports fail after 30 seconds.
Options: stream the rows (about 40 lines, one file) · cap the export at
10,000 rows and say so on the page · leave it.
Recommendation: stream the rows, because a cap hides the failure from the
customers who hit it.
</example>

<example>
`lib/csv.ts:88` quotes a field twice when the value holds a quote mark (not
part of this branch). If left: exported names with quotes show doubled marks.
</example>

After the sections, give a table of the checks and their results. Its last
rows are the scan (`none tagged`, `<n> tagged, see 2` or
`unavailable (<reason>)`) and CodeRabbit (`ran` or `not run (<reason>)`). The
commit message line the style asks for comes last.
