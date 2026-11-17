"""Pure judgement for the builds eval: test results, changed files and the case outcome."""
import fnmatch
from pathlib import PurePosixPath

PASS, FAIL, REGRESSED, NO_CHANGE, ERROR = "pass", "fail", "regressed", "no-change", "error"
FILE_LOAD = "(file failed to load)"
TEST_FILE_GLOBS = ["*.test.*", "*.spec.*", "tests/*", "test/*", "__tests__/*", "*/__tests__/*"]


def outcome(errored, files_changed, hidden_passed, newly_failing):
    if errored:
        return ERROR
    if not files_changed:
        return NO_CHANGE
    if not hidden_passed:
        return FAIL
    if newly_failing:
        return REGRESSED
    return PASS


def suite_statuses(report, root):
    """Map "file > full test name" to its status from a vitest JSON report."""
    statuses = {}
    prefix = str(root).rstrip("/") + "/"
    for file_result in report.get("testResults", []):
        name = file_result.get("name", "")
        name = name[len(prefix):] if name.startswith(prefix) else name
        assertions = file_result.get("assertionResults", [])
        if file_result.get("status") == "failed" and not any(a.get("status") == "failed" for a in assertions):
            statuses[f"{name} > {FILE_LOAD}"] = "failed"
        for assertion in assertions:
            statuses[f"{name} > {assertion.get('fullName') or assertion.get('title')}"] = assertion.get("status")
    return statuses


def newly_failing(baseline, after):
    """Tests that passed in the baseline and now fail, or whose file no longer loads."""
    failed_files = {key.split(" > ", 1)[0] for key, status in after.items() if key.endswith(FILE_LOAD) and status == "failed"}
    return sorted(
        key for key, status in baseline.items()
        if status == "passed"
        and (after.get(key) == "failed" or (key not in after and key.split(" > ", 1)[0] in failed_files))
    )


def changed_files(before, after):
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def is_test_file(path):
    posix = str(PurePosixPath(path))
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(posix, pattern) or fnmatch.fnmatch(name, pattern) for pattern in TEST_FILE_GLOBS)
