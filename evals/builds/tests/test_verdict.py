import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verdict import (  # noqa: E402
    ERROR, FAIL, FILE_LOAD, NO_CHANGE, PASS, REGRESSED,
    changed_files, is_test_file, newly_failing, outcome, suite_statuses,
)

ROOT = "/tmp/build-eval-x/project"


def vitest_report(*files):
    return {"numTotalTests": 0, "testResults": [
        {"name": f"{ROOT}/{name}", "status": status, "message": "",
         "assertionResults": [{"fullName": title, "title": title, "status": s} for title, s in tests]}
        for name, status, tests in files
    ]}


def test_outcome_error_wins_over_everything():
    assert outcome(True, ["a.ts"], True, []) == ERROR


def test_outcome_no_change_when_no_file_changed():
    assert outcome(False, [], True, []) == NO_CHANGE


def test_outcome_fail_when_hidden_tests_fail():
    assert outcome(False, ["a.ts"], False, []) == FAIL


def test_outcome_regressed_when_a_baseline_test_now_fails():
    assert outcome(False, ["a.ts"], True, ["x > y"]) == REGRESSED


def test_outcome_pass():
    assert outcome(False, ["a.ts"], True, []) == PASS


def test_statuses_are_keyed_by_relative_file_and_test_name():
    report = vitest_report(("tests/unit/cart.test.ts", "passed", [("cart adds an item", "passed")]))
    assert suite_statuses(report, ROOT) == {"tests/unit/cart.test.ts > cart adds an item": "passed"}


def test_baseline_comparison_lists_only_tests_that_passed_before():
    baseline = suite_statuses(vitest_report(
        ("tests/unit/cart.test.ts", "failed", [("adds", "passed"), ("removes", "failed"), ("empties", "passed")]),
    ), ROOT)
    after = suite_statuses(vitest_report(
        ("tests/unit/cart.test.ts", "failed", [("adds", "failed"), ("removes", "failed"), ("empties", "passed")]),
    ), ROOT)
    assert newly_failing(baseline, after) == ["tests/unit/cart.test.ts > adds"]


def test_baseline_comparison_counts_a_file_that_no_longer_loads():
    baseline = suite_statuses(vitest_report(("tests/unit/tax.test.ts", "passed", [("rounds", "passed")])), ROOT)
    after = suite_statuses(vitest_report(("tests/unit/tax.test.ts", "failed", [])), ROOT)
    assert after == {f"tests/unit/tax.test.ts > {FILE_LOAD}": "failed"}
    assert newly_failing(baseline, after) == ["tests/unit/tax.test.ts > rounds"]


def test_baseline_comparison_ignores_removed_tests_in_a_loading_file():
    baseline = suite_statuses(vitest_report(("tests/unit/tax.test.ts", "passed", [("rounds", "passed")])), ROOT)
    after = suite_statuses(vitest_report(("tests/unit/tax.test.ts", "passed", [("rounds up", "passed")])), ROOT)
    assert newly_failing(baseline, after) == []


def test_changed_files_covers_edits_additions_and_deletions():
    before = {"lib/a.ts": "1", "lib/b.ts": "2"}
    after = {"lib/a.ts": "9", "lib/c.ts": "3"}
    assert changed_files(before, after) == ["lib/a.ts", "lib/b.ts", "lib/c.ts"]


def test_is_test_file():
    assert is_test_file("tests/unit/cart.test.ts")
    assert is_test_file("lib/cart.spec.ts")
    assert not is_test_file("lib/cart.ts")
