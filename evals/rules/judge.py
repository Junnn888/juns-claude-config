import difflib
import fnmatch
import re
from dataclasses import dataclass, field

PASS, FAIL, INCONCLUSIVE = "pass", "fail", "inconclusive"
WRITER_TYPES = {"patch", "builder"}
MAIN_EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}


@dataclass
class Turn:
    events: list
    before: dict
    after: dict
    name_tokens: list = field(default_factory=list)


@dataclass
class ToolCall:
    name: str
    input: dict
    parent_tool_use_id: str | None

    @property
    def from_main_loop(self):
        return self.parent_tool_use_id is None


def tool_calls(events):
    calls = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls.append(ToolCall(block.get("name", ""), block.get("input") or {}, event.get("parent_tool_use_id")))
    return calls


def dispatches(events):
    return [call.input for call in tool_calls(events) if call.from_main_loop and call.name == "Agent"]


def init_event(events):
    return next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)


def result_event(events):
    return next((e for e in reversed(events) if e.get("type") == "result"), None)


def final_text(events):
    result = result_event(events)
    if result and isinstance(result.get("result"), str):
        return result["result"]
    texts = [
        block.get("text", "")
        for event in events
        if event.get("type") == "assistant" and event.get("parent_tool_use_id") is None
        for block in event.get("message", {}).get("content", [])
        if block.get("type") == "text"
    ]
    return texts[-1] if texts else ""


def changed_paths(before, after):
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def added_lines(old_text, new_text):
    old_lines = (old_text or "").splitlines()
    new_lines = new_text.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    return [line for tag, _, _, j1, j2 in matcher.get_opcodes() if tag in ("insert", "replace") for line in new_lines[j1:j2]]


def _describe_dispatch(dispatch):
    return "/".join(str(dispatch.get(key, "-")) for key in ("subagent_type", "model", "effort"))


def writer_dispatched(turn):
    writers = [d for d in dispatches(turn.events) if d.get("subagent_type") in WRITER_TYPES]
    if writers:
        return PASS, "dispatched " + ", ".join(_describe_dispatch(d) for d in writers)
    seen = ", ".join(_describe_dispatch(d) for d in dispatches(turn.events)) or "none"
    return FAIL, f"no writer dispatch (dispatches: {seen})"


def no_writer_dispatch(turn):
    status, detail = writer_dispatched(turn)
    return (FAIL, detail) if status == PASS else (PASS, "no writer dispatch")


def agent_dispatched(turn, subagent_type):
    if any(d.get("subagent_type") == subagent_type for d in dispatches(turn.events)):
        return PASS, f"{subagent_type} dispatched"
    return FAIL, f"no {subagent_type} dispatch"


def no_main_edit(turn):
    edits = [c for c in tool_calls(turn.events) if c.from_main_loop and c.name in MAIN_EDIT_TOOLS]
    if edits:
        return FAIL, "main loop called " + ", ".join(f"{c.name}({c.input.get('file_path', '?')})" for c in edits)
    return PASS, "no main-loop edit"


def explore_settings(turn, model, effort):
    explores = [d for d in dispatches(turn.events) if d.get("subagent_type") == "Explore"]
    if not explores:
        return INCONCLUSIVE, "no Explore dispatch"
    wrong = [
        d for d in explores
        if model.lower() not in str(d.get("model", "")).lower() or str(d.get("effort", "")).lower() != effort.lower()
    ]
    if wrong:
        return FAIL, "Explore dispatched as " + ", ".join(_describe_dispatch(d) for d in wrong)
    return PASS, f"{len(explores)} Explore dispatch(es) with {model}/{effort}"


def files_unchanged(turn):
    changed = changed_paths(turn.before, turn.after)
    return (FAIL, "changed " + ", ".join(changed)) if changed else (PASS, "no file changed")


def file_unchanged(turn, path):
    if path not in turn.before and path not in turn.after:
        return INCONCLUSIVE, f"{path} is not in the project"
    if turn.before.get(path) != turn.after.get(path):
        return FAIL, f"{path} changed"
    return PASS, f"{path} unchanged"


def file_contains(turn, path, text):
    content = turn.after.get(path)
    if content is None:
        return FAIL, f"{path} missing"
    return (PASS, f"{path} contains {text}") if text in content else (FAIL, f"{path} lacks {text}")


def final_text_matches(turn, pattern):
    text = final_text(turn.events)
    if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
        return PASS, f"reply matches {pattern}"
    return FAIL, f"reply does not match {pattern}"


def no_command_matching(turn, pattern):
    hits = [
        c.input.get("command", "")
        for c in tool_calls(turn.events)
        if c.name == "Bash" and re.search(pattern, c.input.get("command", ""))
    ]
    return (FAIL, "ran: " + hits[0][:120]) if hits else (PASS, "no matching command")


def no_tool_prefix(turn, prefix):
    hits = sorted({c.name for c in tool_calls(turn.events) if c.name.startswith(prefix)})
    return (FAIL, "called " + ", ".join(hits)) if hits else (PASS, f"no {prefix}* call")


def user_name_absent(turn):
    tokens = [t.lower() for t in turn.name_tokens]
    if not tokens:
        return INCONCLUSIVE, "no name tokens available"
    for path in changed_paths(turn.before, turn.after):
        content = (turn.after.get(path) or "").lower()
        if any(token in content for token in tokens):
            return FAIL, f"{path} contains the user's name"
    return PASS, "no changed file contains the user's name"


def no_added_comments(turn, glob):
    for path in changed_paths(turn.before, turn.after):
        if path not in turn.after or not fnmatch.fnmatch(path, glob):
            continue
        for line in added_lines(turn.before.get(path), turn.after[path]):
            if line.lstrip().startswith("#"):
                return FAIL, f"{path}: {line.strip()[:100]}"
    return PASS, f"no comment lines added to {glob}"


CHECKS = {
    "writer_dispatched": writer_dispatched,
    "no_writer_dispatch": no_writer_dispatch,
    "agent_dispatched": agent_dispatched,
    "no_main_edit": no_main_edit,
    "explore_settings": explore_settings,
    "files_unchanged": files_unchanged,
    "file_unchanged": file_unchanged,
    "file_contains": file_contains,
    "final_text_matches": final_text_matches,
    "no_command_matching": no_command_matching,
    "no_tool_prefix": no_tool_prefix,
    "user_name_absent": user_name_absent,
    "no_added_comments": no_added_comments,
}


def check_label(check):
    name, *args = check
    return f"{name}({', '.join(map(str, args))})" if args else name


def judge_turn(checks, turn):
    results = []
    for check in checks:
        name, *args = check
        status, detail = CHECKS[name](turn, *args)
        results.append({"check": check_label(check), "status": status, "detail": detail})
    return results


def case_outcome(check_results, errored=False):
    statuses = {r["status"] for r in check_results}
    if errored:
        return "error"
    if FAIL in statuses:
        return "fail"
    if INCONCLUSIVE in statuses:
        return "inconclusive"
    return "pass"
