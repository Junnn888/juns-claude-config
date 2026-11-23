#!/usr/bin/env python3
import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

FAMILIES = ("fable", "opus", "sonnet", "haiku")
MAIN = "main session"
ADVISOR = "advisor"
HANDOVER_TOOLS = {"Agent", "SendMessage", "Workflow"}
CALL_KINDS = [
    "hand-over to an agent",
    "reply to the user",
    "vault note edit",
    "config edit",
    "other edit",
    "file read",
    "shell command",
    "other tool",
]
PEAK_CONTEXT = 200_000
REREAD_FLOOR = 150_000


UNIT = "list-price dollars, an approximation of the plan meter"
# dollars per million tokens: input, output, cache read as a multiple of input
PRICES = {"fable": (8, 40, 0.025), "opus": (4, 20, 0.05), "sonnet": (2, 10, 0.1), "haiku": (0.10, 0.50, 0.1)}
WRITE_1H, WRITE_5M = 2, 1.25


def cost(usage, model):
    input_price, output_price, read_rate = PRICES.get(family(model), (0, 0, 0))
    split = usage.get("cache_creation") or {}
    if "ephemeral_1h_input_tokens" in split or "ephemeral_5m_input_tokens" in split:
        writes = WRITE_1H * split.get("ephemeral_1h_input_tokens", 0) + WRITE_5M * split.get("ephemeral_5m_input_tokens", 0)
    else:
        writes = WRITE_5M * usage.get("cache_creation_input_tokens", 0)
    input_side = usage.get("input_tokens", 0) + writes + read_rate * usage.get("cache_read_input_tokens", 0)
    return (input_price * input_side + output_price * usage.get("output_tokens", 0)) / 1e6


def advisor_iterations(usage):
    return [i for i in usage.get("iterations") or [] if isinstance(i, dict) and i.get("type") == "advisor_message"]


def context(usage):
    return usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)


def family(model):
    return next((name for name in FAMILIES if name in model), model)


def local_day(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().date()


def classify(blocks):
    tools = [(b.get("name", ""), b.get("input") or {}) for b in blocks if b.get("type") == "tool_use"]
    names = [name for name, _ in tools]
    if not tools:
        return "reply to the user"
    if HANDOVER_TOOLS & set(names):
        return "hand-over to an agent"
    for name, tool_input in tools:
        if name in ("Edit", "Write"):
            path = tool_input.get("file_path", "")
            if "/tolaria" in path:
                return "vault note edit"
            if "/.claude/" in path or "claude-config" in path:
                return "config edit"
            return "other edit"
    if any(name.startswith("mcp__tolaria") for name in names):
        return "vault note edit"
    if "Read" in names:
        return "file read"
    if "Bash" in names:
        return "shell command"
    return "other tool"


def collect_calls(entries):
    """entries: (source file, agent type or None for a main session, parsed line); returns one call per message id."""
    best = {}
    blocks = defaultdict(lambda: defaultdict(list))
    for source, agent_type, line in entries:
        message = line.get("message") or {}
        message_id, usage, model = message.get("id"), message.get("usage"), message.get("model", "?")
        if not message_id or not usage or not line.get("timestamp") or model == "<synthetic>":
            continue
        content = message.get("content")
        if isinstance(content, list):
            blocks[message_id][source] += [b for b in content if isinstance(b, dict)]
        kept = best.get(message_id)
        if kept is None or usage.get("output_tokens", 0) > kept["usage"].get("output_tokens", 0):
            best[message_id] = {"source": source, "agent": agent_type or MAIN, "model": model,
                                "day": local_day(line["timestamp"]), "usage": usage}
    calls = []
    for message_id, call in best.items():
        calls.append({**call, "family": family(call["model"]), "cost": cost(call["usage"], call["model"]),
                      "kind": classify(blocks[message_id][call["source"]])})
        for advice in advisor_iterations(call["usage"]):
            advisor_model = advice.get("model", "?")
            calls.append({**call, "agent": ADVISOR, "model": advisor_model, "usage": advice, "family": family(advisor_model),
                          "cost": cost(advice, advisor_model), "kind": None})
    return calls


def read_transcripts(root, since):
    """Yield (source, agent_type, line) for every usage line in files touched on or after `since`."""
    cutoff = datetime.combine(since, datetime.min.time()).astimezone().timestamp()
    for path in sorted(Path(root).rglob("*.jsonl")):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            text = path.read_text(errors="replace")
        except OSError:
            continue
        agent_type = None
        if path.parent.name == "subagents":
            try:
                agent_type = json.loads(path.with_suffix(".meta.json").read_text()).get("agentType")
            except (OSError, ValueError):
                pass
            agent_type = agent_type or "unknown"
        source = str(path.relative_to(root))
        for raw in text.splitlines():
            if '"usage"' not in raw:
                continue
            try:
                yield source, agent_type, json.loads(raw)
            except ValueError:
                continue


def dollars(value):
    return round(value, 2)


def share(part, whole):
    return round(part / whole, 3) if whole else 0.0


def summarize(calls, since, until, model=None):
    calls = [c for c in calls if since <= c["day"] <= until]
    total = sum(c["cost"] for c in calls)
    main = [c for c in calls if c["agent"] == MAIN]

    by_family = Counter()
    for c in calls:
        by_family[c["family"]] += c["cost"]
    families = [{"family": f, "dollars": dollars(w), "share": share(w, total)} for f, w in by_family.most_common()]

    breakdown = {}
    for f, family_total in by_family.most_common():
        groups = defaultdict(lambda: {"sources": set(), "calls": 0, "cost": 0.0})
        for c in calls:
            if c["family"] == f:
                g = groups[c["agent"]]
                g["sources"].add(c["source"])
                g["calls"] += 1
                g["cost"] += c["cost"]
        order = sorted(groups, key=lambda agent: (agent != MAIN, -groups[agent]["cost"]))
        breakdown[f] = [{"agent": a, "runs": len(groups[a]["sources"]), "calls": groups[a]["calls"],
                         "dollars": dollars(groups[a]["cost"]), "share": share(groups[a]["cost"], family_total)}
                        for a in order]

    if model is None:
        main_use = Counter()
        for c in main:
            main_use[c["family"]] += c["cost"]
        model = main_use.most_common(1)[0][0] if main_use else "fable"
    chosen = [c for c in calls if c["family"] == model]
    chosen_total = sum(c["cost"] for c in chosen)
    per_day = Counter()
    for c in chosen:
        per_day[c["day"]] += c["cost"]
    days = [{"day": d.isoformat(), "dollars": dollars(per_day[d]), "share": share(per_day[d], chosen_total)}
            for d in sorted(per_day)]

    chosen_main = [c for c in main if c["family"] == model]
    main_total = sum(c["cost"] for c in chosen_main)
    kinds = {k: [0, 0.0] for k in CALL_KINDS}
    for c in chosen_main:
        kinds[c["kind"]][0] += 1
        kinds[c["kind"]][1] += c["cost"]
    call_kinds = [{"kind": k, "calls": n, "dollars": dollars(w), "share": share(w, main_total)} for k, (n, w) in kinds.items()]

    contexts = sorted(context(c["usage"]) for c in chosen_main)
    peaks = Counter()
    for c in chosen_main:
        peaks[c["source"]] = max(peaks[c["source"]], context(c["usage"]))
    input_price, _, read_rate = PRICES.get(model, (0, 0, 0))
    reread = sum(input_price * read_rate * max(0, ctx - REREAD_FLOOR) for ctx in contexts) / 1e6
    main_context = {
        "sessions": len(peaks),
        "calls": len(contexts),
        "median_context_k": round(statistics.median(contexts) / 1e3) if contexts else 0,
        "p90_context_k": round(contexts[int(len(contexts) * 0.9)] / 1e3) if contexts else 0,
        "sessions_peaked_over_200k": sum(1 for peak in peaks.values() if peak > PEAK_CONTEXT),
        "reread_over_150k_dollars": dollars(reread),
        "reread_share": share(reread, main_total),
    }

    return {"since": since.isoformat(), "until": until.isoformat(), "unit": UNIT, "total_dollars": dollars(total),
            "families": families, "family_breakdown": breakdown, "model": model, "model_by_day": days,
            "main_call_kinds": call_kinds, "main_context": main_context}


def render(summary):
    out = [f"Cost in {summary['unit']}, {summary['since']} to {summary['until']}: ${summary['total_dollars']:.2f}",
           "", "## By model family"]
    out += [f"{f['family']:28} {f['dollars']:9.2f} {f['share']:6.0%}" for f in summary["families"]]
    for f, rows in summary["family_breakdown"].items():
        out += ["", f"## {f}: main session and subagents", f"{'':28} {'runs':>5} {'calls':>6} {'dollars':>9} {'share':>6}"]
        out += [f"{r['agent']:28} {r['runs']:5d} {r['calls']:6d} {r['dollars']:9.2f} {r['share']:6.0%}"
                for r in rows]
    model = summary["model"]
    out += ["", f"## {model} by day (main sessions and subagents)"]
    out += [f"{d['day']:28} {d['dollars']:9.2f} {d['share']:6.0%}" for d in summary["model_by_day"]]
    out += ["", f"## {model} main-session calls by what the call did", f"{'':28} {'calls':>6} {'dollars':>9} {'share':>6}"]
    out += [f"{k['kind']:28} {k['calls']:6d} {k['dollars']:9.2f} {k['share']:6.0%}" for k in summary["main_call_kinds"]]
    ctx = summary["main_context"]
    out += ["", f"## {model} main-session context",
            f"sessions {ctx['sessions']}, calls {ctx['calls']}, context per call median {ctx['median_context_k']}k, p90 {ctx['p90_context_k']}k",
            f"sessions that peaked over 200k: {ctx['sessions_peaked_over_200k']}",
            f"dollars spent rereading context above 150k: ${ctx['reread_over_150k_dollars']:.2f} ({ctx['reread_share']:.0%})"]
    return "\n".join(out)


def main():
    today = date.today()
    parser = argparse.ArgumentParser(description=f"Claude Code usage in {UNIT}, from local session transcripts")
    parser.add_argument("--since", type=date.fromisoformat, default=today - timedelta(days=6), help="first local day, YYYY-MM-DD (default: 6 days ago)")
    parser.add_argument("--until", type=date.fromisoformat, default=today, help="last local day, YYYY-MM-DD (default: today)")
    parser.add_argument("--model", choices=FAMILIES, help="family for the by-day, call and context sections (default: main sessions' most used)")
    parser.add_argument("--root", type=Path, default=Path.home() / ".claude" / "projects", help="transcripts folder")
    parser.add_argument("--json", action="store_true", help="print the figures as one JSON object")
    args = parser.parse_args()
    if args.since > args.until:
        sys.exit("--since is after --until")
    summary = summarize(collect_calls(read_transcripts(args.root, args.since)), args.since, args.until, args.model)
    print(json.dumps(summary, indent=2) if args.json else render(summary))


if __name__ == "__main__":
    main()
