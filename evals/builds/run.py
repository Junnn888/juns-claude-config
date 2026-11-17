#!/usr/bin/env python3
import argparse
import hashlib
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

BUILDS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILDS_DIR.parent))
sys.path.insert(1, str(BUILDS_DIR.parent / "rules"))

from claude_session import child_env, parse_stream, resolved_config_dir, run_turn, tested_block  # noqa: E402
from judge import WRITER_TYPES, dispatches, init_event, result_event  # noqa: E402
from verdict import changed_files, is_test_file, newly_failing, outcome, suite_statuses  # noqa: E402

CASES_FILE = BUILDS_DIR / "cases.local.json"
RESULTS_DIR = BUILDS_DIR / "results"
TURN_TIMEOUT_SECONDS = 1800
TURN_BUDGET_USD = 10
COMMAND_TIMEOUT_SECONDS = 900
OUTPUT_TAIL_LINES = 30
SNAPSHOT_SKIP_DIRS = {".git", "node_modules", ".next", "out", "build", "dist", "coverage", "test-results",
                      "playwright-report", ".turbo", ".vercel", ".vitest"}
SNAPSHOT_SKIP_FILES = {"tsconfig.tsbuildinfo", "next-env.d.ts"}
TOOL_ENV = {**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0", "CI": "1"}
ERROR_LINE_PATTERNS = [re.compile(r"\w*Error\b"), re.compile(r"\bFAIL\b|No test files")]


def load_cases():
    if not CASES_FILE.exists():
        sys.exit(f"no {CASES_FILE.name}: copy cases.example.json to it and fill in real cases")
    cases = json.loads(CASES_FILE.read_text())
    for case in cases:
        case["repo"] = os.path.expanduser(case["repo"])
    return cases


def sh(args, cwd, stdin=None):
    try:
        proc = subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, env=TOOL_ENV, timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {COMMAND_TIMEOUT_SECONDS}s: {' '.join(map(str, args))}"
    return proc.returncode, (proc.stdout + proc.stderr).decode(errors="replace")


def git_bytes(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout


def export_before_fix(case, project):
    project.mkdir()
    subprocess.run(["tar", "-x", "-C", str(project)], input=git_bytes(case["repo"], "archive", f"{case['fix']}^"), check=True)


def install(project):
    for command in (["bun", "install", "--frozen-lockfile"], ["bun", "install"]):
        code, output = sh(command, project)
        if code == 0:
            return " ".join(command), None
    return None, "install failed: " + tail(output, 3).replace("\n", " | ")


def overlay_fix_tests(case, project):
    for path in case["tests"]:
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_bytes(case["repo"], "show", f"{case['fix']}:{path}"))


def apply_fix_source(case, project):
    """Bring the non-test files to the fix commit; the fix's tests are already overlaid."""
    excludes = [f":(exclude){path}" for path in case["tests"]]
    patch = git_bytes(case["repo"], "diff", "--binary", f"{case['fix']}^", case["fix"], "--", ".", *excludes)
    code, output = sh(["git", "apply", "--whitespace=nowarn", "-"], project, stdin=patch)
    if code != 0:
        raise RuntimeError("could not apply the fix: " + tail(output, 2).replace("\n", " | "))


def run_hidden_tests(case, project):
    code, output = sh(["bunx", "vitest", "run", *case["tests"]], project)
    return code == 0, output


def run_suite(project, report_path):
    """Statuses of the whole unit suite, or None when vitest wrote no report."""
    report_path.unlink(missing_ok=True)
    sh(["bunx", "vitest", "run", "tests/unit", "--reporter=json", f"--outputFile={report_path}"], project)
    if not report_path.exists():
        return None
    return suite_statuses(json.loads(report_path.read_text()), project.resolve())


def snapshot(root):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath, filename)
            if filename in SNAPSHOT_SKIP_FILES or path.is_symlink() or not path.is_file():
                continue
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def tail(text, lines=OUTPUT_TAIL_LINES):
    return "\n".join(text.rstrip().splitlines()[-lines:])


def first_error_line(output):
    for pattern in ERROR_LINE_PATTERNS:
        line = next((line.strip() for line in output.splitlines() if pattern.search(line)), None)
        if line:
            return line
    return tail(output, 1)


def verify_case(case):
    root = Path(tempfile.mkdtemp(prefix="build-verify-"))
    project = root / "project"
    row = {"case": case["id"], "install": None, "fails_before": False, "error_before": "", "passes_after": False, "error_after": ""}
    try:
        export_before_fix(case, project)
        row["install"], error = install(project)
        if error:
            row["error_before"] = error
            return row
        overlay_fix_tests(case, project)
        passed, output = run_hidden_tests(case, project)
        row["fails_before"], row["error_before"] = not passed, first_error_line(output) if not passed else ""
        apply_fix_source(case, project)
        passed, output = run_hidden_tests(case, project)
        row["passes_after"], row["error_after"] = passed, "" if passed else first_error_line(output)
    except (subprocess.CalledProcessError, RuntimeError) as failure:
        row["error_after"] = str(failure)[:200]
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return row


def print_rows(rows):
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]) - 1)]
    for row in rows:
        print("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)) + "  " + str(row[-1]))


def yes_no(flag):
    return "yes" if flag else "no"


def verify(cases, jobs):
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(verify_case, cases))
    rows = [("case", "fails before", "passes after", "usable", "install", "first error line (before; after if it failed)")]
    for r in results:
        error_text = "; after: ".join(filter(None, [r["error_before"], r["error_after"]]))
        rows.append((r["case"], yes_no(r["fails_before"]), yes_no(r["passes_after"]),
                     yes_no(r["fails_before"] and r["passes_after"]), r["install"] or "-", error_text))
    print_rows(rows)
    return 0 if all(r["fails_before"] and r["passes_after"] for r in results) else 1


def run_case(case, label, streams_dir, env, keep):
    root = Path(tempfile.mkdtemp(prefix="build-eval-"))
    project = root / "project"
    started = time.monotonic()
    record = {"case": case["id"], "label": label, "error": None, "install": None, "setup_seconds": None,
              "hidden_tests_passed": False, "hidden_test_output": "", "newly_failing": [], "files_changed": [],
              "changed_test_file": False, "dispatches": [], "cost_usd": 0.0, "duration_ms": 0, "models": [], "sessions": []}
    models, session_id = set(), None
    try:
        export_before_fix(case, project)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        record["install"], record["error"] = install(project)
        baseline = None if record["error"] else run_suite(project, root / "baseline.json")
        if baseline is None and not record["error"]:
            record["error"] = "baseline suite wrote no report"
        record["setup_seconds"] = round(time.monotonic() - started, 1)
        if record["error"]:
            return record

        before = snapshot(project)
        for number, prompt in enumerate((case["report"], case["go"]), start=1):
            stdout, record["error"] = run_turn(prompt, session_id, project, env,
                                               max_budget_usd=TURN_BUDGET_USD, timeout_seconds=TURN_TIMEOUT_SECONDS)
            (streams_dir / f"{label}-turn{number}.jsonl").write_text(stdout)
            events = parse_stream(stdout)
            init = init_event(events)
            if init:
                session_id = init.get("session_id")
                record["sessions"].append({k: init.get(k) for k in ("session_id", "model", "permissionMode", "output_style")})
            result = result_event(events) or {}
            record["cost_usd"] += result.get("total_cost_usd") or 0.0
            record["duration_ms"] += result.get("duration_ms") or 0
            models.update((result.get("modelUsage") or {}).keys())
            record["dispatches"] += [
                {"turn": number, **{k: d.get(k) for k in ("subagent_type", "model", "effort")}} for d in dispatches(events)
            ]
            if record["error"]:
                break

        record["files_changed"] = changed_files(before, snapshot(project))
        record["changed_test_file"] = any(is_test_file(path) for path in record["files_changed"])
        overlay_fix_tests(case, project)
        record["hidden_tests_passed"], output = run_hidden_tests(case, project)
        record["hidden_test_output"] = tail(output)
        after = run_suite(project, root / "after.json")
        record["newly_failing"] = newly_failing(baseline, after) if after is not None else ["(suite wrote no report)"]
    except subprocess.CalledProcessError as failure:
        record["error"] = f"{failure.cmd[:3]} exited {failure.returncode}"
    finally:
        if keep:
            print(f"kept {case['id']}: {project}")
        else:
            shutil.rmtree(root, ignore_errors=True)
        record["models"] = sorted(models)
        record["cost_usd"] = round(record["cost_usd"], 4)
        record["wall_seconds"] = round(time.monotonic() - started, 1)
        record["outcome"] = outcome(record["error"] is not None, record["files_changed"],
                                    record["hidden_tests_passed"], record["newly_failing"])
    return record


def print_table(results):
    rows = [("case", "outcome", "cost", "minutes", "writer dispatches")]
    for r in results:
        writers = [d for d in r["dispatches"] if d["subagent_type"] in WRITER_TYPES]
        writer_text = ", ".join(f"t{d['turn']}:{d['subagent_type']}" for d in writers) or "-"
        if r["error"]:
            writer_text += f"  (error: {r['error']})"
        rows.append((r["label"], r["outcome"], f"${r['cost_usd']:.2f}", f"{r['duration_ms'] / 60000:.1f}", writer_text))
    print_rows(rows)
    counts = {o: sum(r["outcome"] == o for r in results) for o in ("pass", "fail", "regressed", "no-change", "error")}
    print("\n" + ", ".join(f"{n} {o}" for o, n in counts.items())
          + f"  |  total cost ${sum(r['cost_usd'] for r in results):.2f}"
          + f"  |  {sum(r['duration_ms'] for r in results) / 60000:.1f} session minutes")


def main():
    parser = argparse.ArgumentParser(description="Replay past bug fixes and judge each new fix with the test the real fix shipped with.")
    parser.add_argument("--verify", action="store_true", help="check every case's hidden tests fail before the fix and pass after it; no model usage")
    parser.add_argument("--case", action="append", default=[], metavar="ID", help="run only this case (repeatable; the only way to run a reserve)")
    parser.add_argument("--runs", type=int, default=1, help="runs per case")
    parser.add_argument("--jobs", type=int, default=2, help="cases run in parallel")
    parser.add_argument("--config-dir", help="config folder for the child sessions (sets CLAUDE_CONFIG_DIR)")
    parser.add_argument("--keep", action="store_true", help="leave each temp folder in place and print its path")
    args = parser.parse_args()

    cases = load_cases()
    unknown = [c for c in args.case if c not in {case["id"] for case in cases}]
    if unknown:
        parser.error("unknown case: " + ", ".join(unknown))

    if args.verify:
        return verify([case for case in cases if not args.case or case["id"] in args.case], args.jobs)

    selected = [case for case in cases if case["id"] in args.case] if args.case else [case for case in cases if not case.get("reserve")]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    streams_dir = RESULTS_DIR / stamp / "streams"
    streams_dir.mkdir(parents=True)
    env = child_env(args.config_dir)
    config_dir = resolved_config_dir(args.config_dir)

    jobs = [(case, case["id"] if args.runs == 1 else f"{case['id']}-r{n}") for case in selected for n in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda job: run_case(job[0], job[1], streams_dir, env, args.keep), jobs))

    first_session = next((s for r in results for s in r["sessions"]), {})
    summary = {
        "tested": tested_block(first_session, config_dir),
        "cases": results,
        "total_cost_usd": round(sum(r["cost_usd"] for r in results), 4),
    }
    (RESULTS_DIR / stamp / "summary.json").write_text(json.dumps(summary, indent=2))

    print_table(results)
    print(f"summary: {RESULTS_DIR / stamp / 'summary.json'}")
    return 0 if all(r["outcome"] == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
