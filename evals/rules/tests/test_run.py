import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run  # noqa: E402
from cases import CASES  # noqa: E402


def case(case_id):
    return next(c for c in CASES if c["id"] == case_id)


def git_output(project, *args):
    return subprocess.run(["git", *args], cwd=project, check=True, capture_output=True, text=True).stdout


def prepared(case_id):
    project = run.prepare_project(case(case_id))
    try:
        return {
            "status": git_output(project, "status", "--short"),
            "remotes": git_output(project, "remote"),
            "commits": subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=project, capture_output=True, text=True).stdout,
            "upstream": subprocess.run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=project, capture_output=True, text=True).stdout,
        }
    finally:
        shutil.rmtree(project)
        shutil.rmtree(run.origin_path(project), ignore_errors=True)


def test_remote_case_gets_clean_pushed_repo():
    state = prepared("repo-says-push")
    assert state == {"status": "", "remotes": "origin\n", "commits": "1\n", "upstream": "origin/main\n"}


def test_other_cases_get_bare_git_init():
    state = prepared("route-small-change")
    assert state["remotes"] == ""
    assert state["commits"] == ""
    assert state["upstream"] == ""
