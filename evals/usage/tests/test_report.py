import json
import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report import CALL_KINDS, classify, collect_calls, cost, read_transcripts, summarize  # noqa: E402

DAY = date(2026, 11, 17)


def usage(inp=0, out=0, cw=0, cr=0):
    return {"input_tokens": inp, "output_tokens": out, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}


def line(message_id, block, model="claude-fable-x", ts="2026-11-17T04:00:00Z", **tokens):
    return {"type": "assistant", "timestamp": ts,
            "message": {"id": message_id, "model": model, "usage": usage(**tokens), "content": [block]}}


def text(value="ok"):
    return {"type": "text", "text": value}


def tool(name, **tool_input):
    return {"type": "tool_use", "id": "toolu_" + name, "name": name, "input": tool_input}


def write_jsonl(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item) for item in lines) + "\n")


@pytest.fixture
def local_tz(monkeypatch):
    def use(zone):
        monkeypatch.setenv("TZ", zone)
        time.tzset()
    yield use
    monkeypatch.undo()
    time.tzset()


def summary_of(tmp_path, since=DAY, until=DAY, model=None):
    return summarize(collect_calls(read_transcripts(tmp_path, since)), since, until, model)


def split_writes(one_hour=0, five_minute=0):
    return {"cache_creation_input_tokens": one_hour + five_minute,
            "cache_creation": {"ephemeral_1h_input_tokens": one_hour, "ephemeral_5m_input_tokens": five_minute}}


def test_input_and_output_prices():
    assert cost(usage(inp=1_000_000, out=1_000_000), "claude-fable-x") == pytest.approx(48)
    assert cost(usage(inp=1_000_000, out=1_000_000), "claude-opus-x") == pytest.approx(24)
    assert cost(usage(inp=1_000_000, out=1_000_000), "claude-sonnet-x") == pytest.approx(12)
    assert cost(usage(inp=1_000_000, out=1_000_000), "claude-haiku-x") == pytest.approx(0.6)


def test_one_hour_cache_write_at_twice_input():
    assert cost(split_writes(one_hour=1_000_000), "claude-opus-x") == pytest.approx(8)


def test_five_minute_cache_write_at_one_and_a_quarter_input():
    assert cost(split_writes(five_minute=1_000_000), "claude-opus-x") == pytest.approx(5)


def test_cache_writes_without_split_at_one_and_a_quarter_input():
    assert cost(usage(cw=1_000_000), "claude-fable-x") == pytest.approx(10)


@pytest.mark.parametrize("model, dollars", [
    ("claude-fable-x", 8 * 0.025),
    ("claude-opus-x", 4 * 0.05),
    ("claude-sonnet-x", 2 * 0.1),
    ("claude-haiku-x", 0.10 * 0.1),
])
def test_cache_read_rate_per_family(model, dollars):
    assert cost(usage(cr=1_000_000), model) == pytest.approx(dollars)


def test_advisor_counted_to_its_own_model_as_the_advisor_row(tmp_path):
    executor = line("m1", text(), model="claude-opus-x", inp=1_000_000, out=0)
    executor["message"]["usage"]["iterations"] = [
        {"type": "message", "input_tokens": 1_000_000, "output_tokens": 0},
        {"type": "advisor_message", "model": "claude-fable-x", "input_tokens": 1_000_000, "output_tokens": 100_000},
    ]
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [executor])
    summary = summary_of(tmp_path)
    families = {f["family"]: f["dollars"] for f in summary["families"]}
    assert families == {"fable": 12.0, "opus": 4.0}
    assert summary["total_dollars"] == 16.0
    assert summary["family_breakdown"]["fable"] == [
        {"agent": "advisor", "runs": 1, "calls": 1, "dollars": 12.0, "share": 1.0}]
    assert [r["agent"] for r in summary["family_breakdown"]["opus"]] == ["main session"]
    assert summary["main_context"]["calls"] == 1


def test_message_on_several_lines_counted_once_with_largest_output(tmp_path):
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [
        line("m1", text("plan"), inp=10, out=1),
        line("m1", tool("Agent", subagent_type="builder"), inp=10, out=40),
        line("m1", text("more"), inp=10, out=5),
    ])
    calls = collect_calls(read_transcripts(tmp_path, DAY))
    assert len(calls) == 1
    assert calls[0]["usage"]["output_tokens"] == 40
    assert calls[0]["kind"] == "hand-over to an agent"


def test_synthetic_model_skipped(tmp_path):
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [line("m1", text(), model="<synthetic>", out=5)])
    assert collect_calls(read_transcripts(tmp_path, DAY)) == []


@pytest.mark.parametrize("blocks, kind", [
    ([tool("Agent")], "hand-over to an agent"),
    ([tool("SendMessage"), tool("Bash", command="ls")], "hand-over to an agent"),
    ([tool("Workflow")], "hand-over to an agent"),
    ([text()], "reply to the user"),
    ([tool("Edit", file_path="/x/projects/tolaria/note.md")], "vault note edit"),
    ([tool("mcp__tolaria__update_note")], "vault note edit"),
    ([tool("Write", file_path="/x/.claude/agents/builder.md")], "config edit"),
    ([tool("Edit", file_path="/x/juncc/claude-config/CLAUDE.md")], "config edit"),
    ([tool("Edit", file_path="/x/repo/app.py")], "other edit"),
    ([tool("Read", file_path="/x/repo/app.py")], "file read"),
    ([tool("Bash", command="ls")], "shell command"),
    ([tool("Grep", pattern="x")], "other tool"),
])
def test_classify_each_call_kind(blocks, kind):
    assert classify(blocks) == kind


def test_kind_uses_blocks_gathered_across_lines(tmp_path):
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [
        line("m1", text("reading"), out=3),
        line("m1", tool("Read", file_path="/x/a.py"), out=3),
    ])
    kinds = {k["kind"]: k["calls"] for k in summary_of(tmp_path)["main_call_kinds"]}
    assert kinds["file read"] == 1 and sum(kinds.values()) == 1
    assert [k["kind"] for k in summary_of(tmp_path)["main_call_kinds"]] == CALL_KINDS


def test_subagent_run_attributed_to_its_agent_type(tmp_path):
    session = tmp_path / "proj" / "s1"
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [line("m1", text(), out=10)])
    write_jsonl(session / "subagents" / "agent-a1.jsonl", [
        line("m2", tool("Read", file_path="/x"), model="claude-opus-x", out=10),
        line("m3", text(), model="claude-opus-x", out=10),
    ])
    (session / "subagents" / "agent-a1.meta.json").write_text(json.dumps({"agentType": "builder"}))
    summary = summary_of(tmp_path)
    assert summary["family_breakdown"]["opus"] == [
        {"agent": "builder", "runs": 1, "calls": 2, "dollars": 0.0, "share": 1.0}]
    assert summary["family_breakdown"]["fable"][0]["agent"] == "main session"
    assert summary["main_context"]["calls"] == 1


def test_date_filter_inclusive_in_local_time(tmp_path, local_tz):
    local_tz("Asia/Singapore")
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [
        line("before", text(), ts="2026-11-15T15:59:00Z", out=1),  # 23:59 on 15 Nov local
        line("first", text(), ts="2026-11-15T16:00:00Z", out=1),   # 00:00 on 16 Nov local
        line("last", text(), ts="2026-11-17T15:59:00Z", out=2),    # 23:59 on 17 Nov local
        line("after", text(), ts="2026-11-17T16:00:00Z", out=1),   # 00:00 on 18 Nov local
    ])
    summary = summary_of(tmp_path, since=date(2026, 11, 16), until=date(2026, 11, 17))
    assert summary["main_context"]["calls"] == 2
    assert [d["day"] for d in summary["model_by_day"]] == ["2026-11-16", "2026-11-17"]


def test_context_section(tmp_path):
    write_jsonl(tmp_path / "proj" / "s1.jsonl", [
        line("m1", text(), cr=100_000, out=1),
        line("m2", text(), cr=250_000, out=1),
    ])
    write_jsonl(tmp_path / "proj" / "s2.jsonl", [line("m3", text(), cr=120_000, out=1)])
    ctx = summary_of(tmp_path)["main_context"]
    assert ctx["sessions"] == 2 and ctx["calls"] == 3
    assert ctx["median_context_k"] == 120
    assert ctx["sessions_peaked_over_200k"] == 1
    assert ctx["reread_over_150k_dollars"] == pytest.approx(0.02)  # 100k at Fable's $0.20 per million read
