Write no comments in code; let names and structure explain it. If code seems to need a comment, change the code until it doesn't, and if you can't, put the why in the plan, or in the build report when there is no plan. Leave existing comments unless the change makes them wrong, and write doc comments only where the repo's instructions ask for them. A lint or type directive is not a comment, and each one added is named in the report. Put known limits and follow-ups in the reply and the PR notes.

Refer to the user as "the user" (they/them) in everything you write: code, comments, commit messages, PR descriptions, files, notes, dispatches and replies. Their name goes in only when they ask for it.

A planning reply ends with the plan and stops. A pick, an answer or a decision from the user is a decision: record it and reply. Start a build when the user tells you to start.

The user runs the dev server. When a step needs the running app, use the server whose working folder is this checkout. If there is none, tell the user which checkout needs one and what for, then wait.

The user decides what is installed on this computer. When a task needs a runtime, tool or version that is missing, stop and tell the user which prerequisite is missing and what needs it, then wait for their answer. A subagent stops and reports the missing prerequisite to the session that dispatched it, which asks the user.

For anything about env variables, read `.env.example`. When a real env file needs a change, print the lines for the user to paste. A change that adds or renames an env variable updates `.env.example` in the same change.

Use the local development database as the work needs. When a task needs data from a live or hosted database, write the SQL statement for the user to run, and work from the result they give back.

Run browser checks against the local app in Playwright. Use Claude in Chrome when the check needs the user's real signed-in session, or when the user asks for it.

Before running tests or browser checks, read `~/.claude/machine.md` if it exists and use the worker limits it records; otherwise start with the project's defaults. When a run stalls the dev server or times out under load, rerun it with fewer workers and add a line to `~/.claude/machine.md` saying what worked and why.
