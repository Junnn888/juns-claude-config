#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases import CASES  # noqa: E402
from claude_session import child_env, command_output, parse_stream, resolved_config_dir, run_turn, tested_block  # noqa: E402
from judge import Turn, case_outcome, dispatches, init_event, judge_turn, result_event  # noqa: E402

RULES_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = RULES_DIR / "fixtures"
RESULTS_DIR = RULES_DIR.parent / "results"
SNAPSHOT_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}


def user_name_tokens():
    sources = [
        command_output(["git", "config", "--global", "user.name"]),
        command_output(["git", "config", "--global", "user.email"]).split("@")[0],
        os.environ.get("USER", ""),
        command_output(["id", "-F"]),
    ]
    tokens = set()
    for source in sources:
        tokens.add(source)
        tokens.update(re.split(r"[^A-Za-z0-9]+", source))
    return sorted(t.lower() for t in tokens if len(t) >= 4)


def snapshot(root):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath, filename)
            files[str(path.relative_to(root))] = path.read_bytes().decode("utf-8", errors="replace")
    return files


def origin_path(project):
    return project.with_name(f"{project.name}-origin.git")


def git(project, *args):
    subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)


def add_pushed_origin(project):
    origin = origin_path(project)
    git(project.parent, "init", "-q", "--bare", "-b", "main", str(origin))
    (project / ".gitignore").write_text(".env\n__pycache__/\n")
    git(project, "checkout", "-q", "-b", "main")
    git(project, "remote", "add", "origin", str(origin))
    git(project, "add", "-A")
    git(project, "-c", "user.name=Eval Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "Initial greeter")
    git(project, "push", "-q", "-u", "origin", "main")


def prepare_project(case):
    project = Path(tempfile.mkdtemp(prefix="config-eval-"))
    shutil.copytree(FIXTURES_DIR / "base", project, dirs_exist_ok=True)
    if case["fixture"] != "base":
        shutil.copytree(FIXTURES_DIR / "overlays" / case["fixture"], project, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    if case.get("git") == "remote":
        add_pushed_origin(project)
    return project


def run_case(case, label, streams_dir, env, name_tokens):
    project = prepare_project(case)
    started = time.monotonic()
    check_results, seen_dispatches, models, inits = [], [], set(), []
    cost, duration_ms, error, session_id = 0.0, 0, None, None
    try:
        before = snapshot(project)
        for number, turn_spec in enumerate(case["turns"], start=1):
            stdout, error = run_turn(turn_spec["prompt"], session_id, project, env)
            (streams_dir / f"{label}-turn{number}.jsonl").write_text(stdout)
            events = parse_stream(stdout)
            after = snapshot(project)
            init = init_event(events)
            if init:
                session_id = init.get("session_id")
                inits.append({k: init.get(k) for k in ("session_id", "model", "permissionMode", "output_style")})
            result = result_event(events) or {}
            cost += result.get("total_cost_usd") or 0.0
            duration_ms += result.get("duration_ms") or 0
            models.update((result.get("modelUsage") or {}).keys())
            seen_dispatches += [
                {"turn": number, **{k: d.get(k) for k in ("subagent_type", "model", "effort")}} for d in dispatches(events)
            ]
            if error:
                break
            for check in judge_turn(turn_spec["checks"], Turn(events, before, after, name_tokens)):
                check_results.append({"turn": number, **check})
            before = after
    finally:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(origin_path(project), ignore_errors=True)
    return {
        "case": case["id"],
        "label": label,
        "rule": case["rule"],
        "outcome": case_outcome(check_results, errored=error is not None),
        "error": error,
        "checks": check_results,
        "cost_usd": round(cost, 4),
        "duration_ms": duration_ms,
        "wall_seconds": round(time.monotonic() - started, 1),
        "models": sorted(models),
        "dispatches": seen_dispatches,
        "sessions": inits,
    }


def print_table(results):
    rows = [("case", "rule", "outcome", "failed checks", "cost")]
    for r in results:
        failed = [f"t{c['turn']}:{c['check']}" for c in r["checks"] if c["status"] == "fail"]
        if r["error"]:
            failed.append(f"error: {r['error']}")
        rows.append((r["label"], r["rule"], r["outcome"], "; ".join(failed) or "-", f"${r['cost_usd']:.2f}"))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) + "  " + row[4])
    counts = {o: sum(r["outcome"] == o for r in results) for o in ("pass", "fail", "inconclusive", "error")}
    total_cost = sum(r["cost_usd"] for r in results)
    print("\n" + ", ".join(f"{n} {o}" for o, n in counts.items()) + f"  |  total cost ${total_cost:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Check that the Claude Code config behaves as its rules say.")
    parser.add_argument("--list", action="store_true", help="print case ids and rules, run nothing")
    parser.add_argument("--case", action="append", default=[], metavar="ID", help="run only this case (repeatable)")
    parser.add_argument("--runs", type=int, default=1, help="runs per case")
    parser.add_argument("--jobs", type=int, default=3, help="cases run in parallel")
    parser.add_argument("--config-dir", help="config folder for the child sessions (sets CLAUDE_CONFIG_DIR)")
    args = parser.parse_args()

    if args.list:
        for case in CASES:
            print(f"{case['id']:<26} {case['rule']}")
        return 0

    known = {case["id"] for case in CASES}
    unknown = [c for c in args.case if c not in known]
    if unknown:
        parser.error("unknown case: " + ", ".join(unknown))
    selected = [case for case in CASES if not args.case or case["id"] in args.case]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    streams_dir = RESULTS_DIR / stamp / "streams"
    streams_dir.mkdir(parents=True)
    env = child_env(args.config_dir)
    name_tokens = user_name_tokens()
    config_dir = resolved_config_dir(args.config_dir)

    jobs = [(case, case["id"] if args.runs == 1 else f"{case['id']}-r{n}") for case in selected for n in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda job: run_case(job[0], job[1], streams_dir, env, name_tokens), jobs))

    first_session = next((s for r in results for s in r["sessions"]), {})
    summary = {
        "tested": tested_block(first_session, config_dir),
        "cases": results,
        "total_cost_usd": round(sum(r["cost_usd"] for r in results), 4),
    }
    (RESULTS_DIR / stamp / "summary.json").write_text(json.dumps(summary, indent=2))

    print_table(results)
    print(f"summary: {RESULTS_DIR / stamp / 'summary.json'}")
    return 1 if any(r["outcome"] in ("fail", "error") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
