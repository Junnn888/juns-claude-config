#!/usr/bin/env python3
"""Score recent Claude Code transcripts against the orchestration config.
Columns: session, turns (distinct main-loop assistant message ids), edits by main, repo reads by main (main-loop Read/Bash reads of the repo
instead of dispatching Explore), dispatches, patch×N, patch no-Files, patch outside (paths a patch agent edited beyond its Files:),
reports w/o Reused (builder/patch final reports lacking a Reused:/Wrote new: line), Explore on Fable, Explore via docs, builder→deep,
fix-it resends, replies w/o Next, avg words, corrections (user turns opening with a pushback phrase), picks w/ reason (user replies to a gate or
"Yours to decide" ask that carry a reason, over all such replies), gate waved (final reports saying the gate was waved), $proxy, fable%, cache_rd M, output tokens by model.
Usage: retro.py [N sessions, default 10] [project-slug substring]"""
import collections, glob, json, os, re, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
FILT = sys.argv[2] if len(sys.argv) > 2 else ""
root = os.path.expanduser("~/.claude/projects")
files = [f for f in glob.glob(f"{root}/*/*.jsonl") if FILT in f]
files = sorted(files, key=os.path.getmtime)[-N:]
CORR = re.compile(r"\bno[,.!]|\bnope\b|\bwrong\b|\bactually\b|\bi meant\b|\bnot what i\b|\bnot my intention\b|\bi did(n't| not) want\b|\bdon't want\b|\bthat('s| is) not\b|\bshould you not\b"
                  r"|\bwhy (did|do|does|are) you\b|\breach(ed)? outside\b|\bnah\b|\bplease remove\b|\bi'?m confused\b|\bstill (broken|there|suffer)|\bagain\b.*\bissue\b|\brather\b|\binstead\b", re.I)  # searched in a prompt's first 240 chars
GATE_ASK = re.compile(r"Which shape, and why|Pick per item, with a one-line why", re.I)  # the main loop asked for a pick with a reason; the follow-up "and why?" is not a second gate
REASON = re.compile(r"\b(because|since|so that|as it|as the|otherwise|given)\b", re.I)  # or more than eight words; measures habit, not quality
WAVED = re.compile(r"gate was waved", re.I)
HOME = os.path.expanduser("~")
SKIP = ("/private/tmp", "/tmp", "~/.claude", "~/projects/tolaria", HOME + "/.claude", HOME + "/projects/tolaria")
READ_VERB = re.compile(r"(?:^|&&|;|\|)\s*(cat|sed -n|head|tail|grep|rg|git show|git diff|git log|find|ls|wc)\b")
HANDBACK = re.compile(r'Another Claude session sent a message:\n<agent-message from="([^"]+)">')
REPORT_LINE = re.compile(r"\b(Reused|Wrote new):")  # the hand-back label, wherever it sits on the line (bullets, bold, after "Files changed")
EDIT = {"Edit", "Write", "NotebookEdit"}
# API list prices 2026-10-06, proxy only. $ per million tokens: input, output, cache write, cache read. Matched by model-name prefix.
PRICES = {"claude-fable-5": (10, 50, 12.5, 0.25), "claude-opus-5-5": (4, 20, 5, 0.20),
          "claude-sonnet-5-5": (2, 10, 2.5, 0.20), "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01)}
def price(model): return next((v for k, v in PRICES.items() if model.startswith(k)), PRICES["claude-sonnet-5-5"])
BASH_EDIT = re.compile(r"sed -i|perl -0?pi|python3 - <<|cat > [^/~]")
PATH_TOK = re.compile(r"[\w@.\[\]()~-]*(?:/[\w@.\[\]()~-]+)+\.\w+")  # any slash path ending in an extension; callers cut heredoc bodies first
USE = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

def in_scope(p, cwd):  # relative, or under cwd, and not scratch/config space
    return not p.startswith(SKIP) and (not p.startswith(("/", "~")) or bool(cwd) and p.startswith(cwd + "/"))

def norm(p, cwd): return re.sub(r"^\./", "", p.lstrip("@").removeprefix(cwd + "/"))

def lines(path):
    for raw in open(path):
        try: yield json.loads(raw)
        except json.JSONDecodeError: pass

def tally(m, msg):  # one transcript line per content block, all sharing message.id: keep the fullest, sum once in settle()
    u, key = msg.get("usage") or {}, msg.get("id") or len(m["seen"])
    if key not in m["seen"] or u.get("output_tokens", 0) >= m["seen"][key][1].get("output_tokens", 0): m["seen"][key] = (msg.get("model", "?"), u)

def settle(m):
    for mod, u in m["seen"].values():
        m["tokens"][mod] += u.get("output_tokens", 0)
        for k in USE: m["use"][mod][k] += u.get(k, 0)

rows = []
for f in files:
    sid = os.path.basename(f)[:8]
    m = dict(edits=0, turn_ids=set(), repo_reads=0, dispatch=collections.Counter(), explore_fable=0, builder=0, deep=0,
             fixit=0, docs_first=0, patch=0, patch_nofiles=0, outside=0, no_reused=0, replies=0, no_next=0, words=0, corrections=0, picks=0, pick_reason=0, waved=0, tokens=collections.Counter(),
             use=collections.defaultdict(collections.Counter), seen={})
    pending, files_by, cwd0, handback = None, {}, "", {}  # files_by: Agent tool_use id -> paths on the patch dispatch's Files: line; handback: agentId -> report text
    for d in lines(f):
        t, msg = d.get("type"), d.get("message") or {}
        cwd0 = cwd0 or d.get("cwd") or ""
        if t == "assistant" and not d.get("isSidechain"):
            tally(m, msg)
            m["turn_ids"].add(msg.get("id"))
            for b in msg.get("content") or []:
                if b.get("type") == "text" and b["text"].strip():
                    pending = b["text"]
                    if WAVED.search(pending): m["waved"] += 1
                if b.get("type") != "tool_use": continue
                n, inp = b["name"], b.get("input") or {}
                if n in EDIT: m["edits"] += 1
                cmd = inp.get("command", "")
                if n == "Bash" and BASH_EDIT.search(cmd): m["edits"] += 1  # shell edits count too
                if n == "Read" and (inp.get("file_path") or "").startswith(cwd0 + "/") and in_scope(inp["file_path"], cwd0): m["repo_reads"] += 1
                if n == "Bash" and READ_VERB.search(cmd) and not BASH_EDIT.search(cmd) and not re.search(r"\bcat\s*>", cmd):
                    # a read counts when some token is a path (has a slash or an extension) in scope
                    toks = [x.strip("\"'") for x in cmd.split()]
                    if any(("/" in x or re.search(r"\w\.[A-Za-z]\w*$", x)) and not x.startswith("-") and in_scope(x, cwd0) for x in toks): m["repo_reads"] += 1
                if n == "Agent":
                    st, mo = inp.get("subagent_type") or "general", inp.get("model") or "inherit"
                    m["dispatch"][f"{st}/{mo}"] += 1
                    if st == "Explore" and mo == "inherit": m["explore_fable"] += 1
                    if st == "Explore" and "ux-flow" in json.dumps(inp): m["docs_first"] += 1
                    if st == "builder": m["builder"] += 1
                    if st == "patch":
                        m["patch"] += 1
                        fl = re.search(r"^Files:(.*)$", inp.get("prompt", ""), re.M)
                        m["patch_nofiles"] += not fl
                        files_by[b["id"]] = set(re.findall(r"[^\s,`]+", fl.group(1))) if fl else set()
                    if st == "deep" and m["builder"]: m["deep"] += 1
                if n == "SendMessage" and re.search(r"\bfix\b", json.dumps(inp), re.I): m["fixit"] += 1
        elif t == "user" and isinstance(msg.get("content"), str):
            c = msg["content"]
            if pending:
                m["replies"] += 1; m["words"] += len(pending.split())
                if not re.search(r"\bNext:", pending): m["no_next"] += 1
                if GATE_ASK.search(pending) and not c.startswith(("<", "Another Claude session")):
                    m["picks"] += 1; m["pick_reason"] += bool(REASON.search(c) or len(c.split()) > 8)
                pending = None
            hb = HANDBACK.match(c)
            if hb and "[Subagent hand-back]" in c: handback[hb.group(1)] = c
            elif not c.startswith(("<", "Another Claude session")) and CORR.search(c[:240]): m["corrections"] += 1
    if pending:  # last reply of a session has no user turn after it
        m["replies"] += 1; m["words"] += len(pending.split())
        if not re.search(r"\bNext:", pending): m["no_next"] += 1
    # subagent transcripts live in a sibling dir named after the session; .meta.json beside each gives agentType and the dispatching toolUseId
    for sf in glob.glob(f[:-6] + "/**/*.jsonl", recursive=True):
        try: meta = json.load(open(sf[:-6] + ".meta.json"))
        except (OSError, json.JSONDecodeError): meta = {}
        kind, edited, last, cwd = meta.get("agentType"), set(), "", ""
        for d in lines(sf):
            cwd = cwd or d.get("cwd") or ""
            if d.get("type") != "assistant": continue
            msg = d.get("message") or {}
            tally(m, msg)
            for b in msg.get("content") or []:
                if b.get("type") == "text" and b["text"].strip(): last = b["text"]
                if b.get("type") != "tool_use": continue
                inp = b.get("input") or {}
                if b["name"] in EDIT and inp.get("file_path"): edited.add(inp["file_path"])
                if b["name"] == "Bash" and BASH_EDIT.search(inp.get("command", "")): edited.update(p for p in PATH_TOK.findall(inp["command"].split("<<")[0]) if in_scope(p, cwd))  # drop heredoc body
        aid = os.path.basename(sf)[6:-6]  # agent-<agentId>.jsonl; the async hand-back in the parent is the real report, the last text only for sync dispatches
        if kind in ("builder", "patch") and not REPORT_LINE.search(handback.get(aid) or last): m["no_reused"] += 1
        if kind == "patch":  # unlinked transcript: compare against every patch dispatch's Files:
            allowed = files_by.get(meta.get("toolUseId")) or set().union(*files_by.values())
            m["outside"] += len({norm(p, cwd) for p in edited} - {norm(p, cwd) for p in allowed})
    settle(m)
    rows.append((sid, m))

print("| session | turns | edits by main | repo reads by main | dispatches | patch×N | patch no-Files | patch outside | reports w/o Reused | Explore on Fable | Explore via docs | builder→deep | fix-it resends | replies w/o Next | avg words | corrections | picks w/ reason | gate waved | $proxy | fable% | cache_rd M | output tokens by model |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for sid, m in rows:
    disp = ", ".join(f"{k}×{v}" for k, v in m["dispatch"].most_common()) or "-"
    tok = ", ".join(f"{k.replace('claude-','')}:{v//1000}k" for k, v in m["tokens"].most_common()) or "-"
    cost = {k: sum(n * p for n, p in zip((u["input_tokens"], m["tokens"][k], u["cache_creation_input_tokens"], u["cache_read_input_tokens"]), price(k))) / 1e6
            for k, u in ((k, m["use"][k]) for k in set(m["tokens"]) | set(m["use"]))}
    total = sum(cost.values()); fable = sum(c for k, c in cost.items() if k.startswith("claude-fable"))
    cache_rd = sum(u["cache_read_input_tokens"] for u in m["use"].values()) / 1e6
    avg = m["words"] // m["replies"] if m["replies"] else 0
    print(f"| {sid} | {len(m['turn_ids'])} | {m['edits']} | {m['repo_reads']} | {disp} | {m['patch']} | {m['patch_nofiles']} | {m['outside']} | {m['no_reused']} | {m['explore_fable']} | {m['docs_first']} | {m['deep']} | {m['fixit']} | {m['no_next']}/{m['replies']} | {avg} | {m['corrections']} | {m['pick_reason']}/{m['picks']} | {m['waved']} | {total:.2f} | {round(100 * fable / total) if total else 0} | {cache_rd:.1f} | {tok} |")
