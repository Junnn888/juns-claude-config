# Config rule evals

Each case runs a real `claude -p` session in a throwaway copy of `rules/fixtures/` and judges the recorded tool calls.

```
python3 evals/rules/run.py --list                     # case ids and the rule each tests
python3 evals/rules/run.py                            # every case (costs real usage)
python3 evals/rules/run.py --case route-small-change  # one case; repeat --case for more
python3 evals/rules/run.py --runs 3 --jobs 3          # repeat each case, 3 at a time
python3 evals/rules/run.py --config-dir PATH          # benchmark another config folder
python3 -m pytest evals/rules/tests -q                # the judge's own tests
```

Reading the output:
- `pass`: every check held. `fail`: a check failed; the table names it as `t<turn>:<check>`.
- `inconclusive`: a check could not apply (e.g. no Explore dispatch to inspect).
- `error`: a turn timed out or exited without a result event; not a verdict on the config.
- Exit code is 1 when any case failed or errored.
- `evals/results/<stamp>/summary.json` holds each check's detail, cost, models and dispatches,
  plus `tested`: the Claude Code version, model, permission mode, output style and a hash of the config files.
  Compare `tested.config_hash` across runs to tie results to a config change.
- Raw streams sit in `evals/results/<stamp>/streams/` (git-ignored).

# Build evals

Each case replays a past bug fix: the code from before the fix goes into a temp folder, a session gets the bug report, and the test the real fix shipped with judges the result.
Real cases live in `builds/cases.local.json` (git-ignored); `builds/cases.example.json` shows the shape.

```
python3 evals/builds/run.py --verify              # hidden tests fail before each fix and pass after it; no model usage
python3 evals/builds/run.py                       # every non-reserve case (costs real usage)
python3 evals/builds/run.py --case ID --keep      # one case; keep its temp folder (holds private code)
python3 -m pytest evals/builds/tests -q           # the outcome function's own tests
```

Outcomes: `pass`, `fail` (hidden tests fail), `regressed` (a baseline-passing test now fails), `no-change`, `error`.
`evals/builds/results/<stamp>/summary.json` (git-ignored) holds each case's test output, files changed, dispatches, cost and the `tested` block.

# Usage report

Reads the local session transcripts under `~/.claude/projects` and reports cost in list-price dollars, an approximation of the plan meter, so a week on one main-session model can be compared with a week on another. No model usage.

```
python3 evals/usage/report.py                                         # last 7 days, local dates
python3 evals/usage/report.py --since 2026-11-16 --until 2026-11-22   # both days inclusive
python3 evals/usage/report.py --model opus                            # family for the by-day, call and context sections
python3 evals/usage/report.py --json > week.json                      # same figures as one JSON object, to diff two periods
python3 -m pytest evals/usage/tests -q                                # the report's own tests
```

Unit: list-price dollars, an approximation of the plan meter. Each message id counts once.
Per million tokens, input / output: Fable $8 / $40, Opus $4 / $20, Sonnet $2 / $10, Haiku $0.10 / $0.50.
Cache writes cost 2 × input for 1-hour writes and 1.25 × input for 5-minute writes (1.25 × when the transcript has no split);
cache reads cost 0.025 × input on Fable, 0.05 × on Opus and 0.1 × on Sonnet and Haiku.
Advisor calls (`advisor_message` entries in `usage.iterations`) count to the advisor's own model and show as the `advisor` row.
Sections: totals by model family; each family split into main session and subagent types (runs, calls);
the chosen family by day (`--model`, default the main sessions' most used); that family's main-session calls by what the call did;
and its main-session context (median and p90 per call, sessions that peaked over 200k, dollars spent rereading context above 150k).
