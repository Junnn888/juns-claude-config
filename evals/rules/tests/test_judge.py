import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import judge  # noqa: E402
from judge import FAIL, INCONCLUSIVE, PASS, Turn  # noqa: E402

STREAMS = Path(__file__).parent / "streams"
AGENT_ID = "toolu_agent_1"


def load(name):
    return [json.loads(line) for line in (STREAMS / name).read_text().splitlines()]


def assistant(parent, *blocks):
    return {"type": "assistant", "parent_tool_use_id": parent, "message": {"model": "claude-main", "content": list(blocks)}}


def tool_use(name, **tool_input):
    return {"type": "tool_use", "id": "toolu_x", "name": name, "input": tool_input}


def dispatch(subagent_type, **extra):
    return assistant(None, tool_use("Agent", subagent_type=subagent_type, prompt="do it", **extra))


def turn(events=(), before=None, after=None, name_tokens=()):
    before = before if before is not None else {}
    return Turn(list(events), before, after if after is not None else dict(before), list(name_tokens))


def status(check, *args, **turn_args):
    return check(turn(**turn_args), *args)[0]


def test_writer_dispatch_seen_in_recorded_shape():
    events = load("edit_via_patch.jsonl")
    assert status(judge.writer_dispatched, events=events) == PASS
    assert status(judge.no_writer_dispatch, events=events) == FAIL
    assert status(judge.agent_dispatched, "patch", events=events) == PASS


def test_writer_dispatch_not_seen():
    events = load("question_via_explore.jsonl")
    assert status(judge.writer_dispatched, events=events) == FAIL
    assert status(judge.no_writer_dispatch, events=events) == PASS
    assert status(judge.agent_dispatched, "Explore", events=events) == PASS
    assert status(judge.agent_dispatched, "deep", events=events) == FAIL


def test_builder_counts_as_writer():
    assert status(judge.writer_dispatched, events=[dispatch("builder")]) == PASS


def test_agent_edit_is_not_a_main_edit():
    assert status(judge.no_main_edit, events=load("edit_via_patch.jsonl")) == PASS


def test_main_loop_edit_fails():
    events = [assistant(None, tool_use("Write", file_path="/work/project/hello.py", content="x"))]
    assert status(judge.no_main_edit, events=events) == FAIL


def test_explore_settings_pass():
    assert status(judge.explore_settings, "sonnet", "medium", events=load("question_via_explore.jsonl")) == PASS


def test_explore_settings_fail_when_any_dispatch_differs():
    events = [dispatch("Explore", model="sonnet", effort="medium"), dispatch("Explore", model="haiku")]
    assert status(judge.explore_settings, "sonnet", "medium", events=events) == FAIL


def test_explore_settings_inconclusive_without_explore():
    assert status(judge.explore_settings, "sonnet", "medium", events=load("edit_via_patch.jsonl")) == INCONCLUSIVE


def test_files_unchanged():
    before = {"hello.py": "a\n"}
    assert status(judge.files_unchanged, before=before) == PASS
    assert status(judge.files_unchanged, before=before, after={"hello.py": "b\n"}) == FAIL
    assert status(judge.files_unchanged, before=before, after={**before, "new.py": ""}) == FAIL
    assert status(judge.files_unchanged, before=before, after={}) == FAIL


def test_file_unchanged_and_contains():
    before = {".env": "A=1\n", ".env.example": "A=\n"}
    after = {".env": "A=1\n", ".env.example": "A=\nFEATURE_FORMAL=\n"}
    assert status(judge.file_unchanged, ".env", before=before, after=after) == PASS
    assert status(judge.file_unchanged, ".env.example", before=before, after=after) == FAIL
    assert status(judge.file_unchanged, "missing", before=before, after=after) == INCONCLUSIVE
    assert status(judge.file_contains, ".env.example", "FEATURE_FORMAL", before=before, after=after) == PASS
    assert status(judge.file_contains, ".env", "FEATURE_FORMAL", before=before, after=after) == FAIL
    assert status(judge.file_contains, "missing", "x", before=before, after=after) == FAIL


def test_final_text_matches_reads_result_event():
    events = load("question_via_explore.jsonl")
    assert status(judge.final_text_matches, r"returns 'HI sam'", events=events) == PASS
    assert status(judge.final_text_matches, r"^\s*\|", events=events) == FAIL


def test_final_text_falls_back_to_last_main_loop_text():
    events = [assistant(None, {"type": "text", "text": "| a | b |"}), assistant(AGENT_ID, {"type": "text", "text": "agent"})]
    assert status(judge.final_text_matches, r"^\s*\|", events=events) == PASS


def test_no_command_matching_catches_an_agents_command():
    events = [assistant(AGENT_ID, tool_use("Bash", command="python3 -m http.server 8000"))]
    assert status(judge.no_command_matching, r"http\.server", events=events) == FAIL
    assert status(judge.no_command_matching, r"psql", events=events) == PASS


def test_no_tool_prefix():
    events = [assistant(AGENT_ID, tool_use("mcp__playwright__browser_navigate", url="http://localhost"))]
    assert status(judge.no_tool_prefix, "mcp__playwright__", events=events) == FAIL
    assert status(judge.no_tool_prefix, "mcp__other__", events=events) == PASS


def test_user_name_absent():
    before = {"README.md": "Old text by Jordan\n"}
    tokens = ["jordan"]
    assert status(judge.user_name_absent, before=before, name_tokens=tokens) == PASS
    after = {"README.md": "## Maintainer\nJORDAN Doe\n"}
    assert status(judge.user_name_absent, before=before, after=after, name_tokens=tokens) == FAIL
    after = {"README.md": "## Maintainer\nThe user\n"}
    assert status(judge.user_name_absent, before=before, after=after, name_tokens=tokens) == PASS
    assert status(judge.user_name_absent, before=before, after=after) == INCONCLUSIVE


def test_no_added_comments():
    before = {"hello.py": "# existing note\ndef greet():\n    pass\n", "notes.md": ""}
    clean = {**before, "hello.py": before["hello.py"] + "x = 1\n"}
    assert status(judge.no_added_comments, "*.py", before=before, after=clean) == PASS
    commented = {**before, "hello.py": before["hello.py"] + "    # now formal\n"}
    assert status(judge.no_added_comments, "*.py", before=before, after=commented) == FAIL
    new_file = {**before, "pkg/extra.py": "# header\n"}
    assert status(judge.no_added_comments, "*.py", before=before, after=new_file) == FAIL
    markdown = {**before, "notes.md": "# Heading\n"}
    assert status(judge.no_added_comments, "*.py", before=before, after=markdown) == PASS


def test_judge_turn_and_outcome():
    t = turn(events=load("question_via_explore.jsonl"))
    results = judge.judge_turn([("no_writer_dispatch",), ("explore_settings", "sonnet", "medium")], t)
    assert [r["check"] for r in results] == ["no_writer_dispatch", "explore_settings(sonnet, medium)"]
    assert judge.case_outcome(results) == "pass"
    assert judge.case_outcome(results + [{"status": INCONCLUSIVE}]) == "inconclusive"
    assert judge.case_outcome(results + [{"status": INCONCLUSIVE}, {"status": FAIL}]) == "fail"
    assert judge.case_outcome(results, errored=True) == "error"
