#!/usr/bin/env python3
"""Gate-integrity scan: list hunks in the branch diff that weaken a gate. Report only, never judges.

Scans added lines (plus removed test declarations) in the diff from merge-base(<base>, HEAD) to the working
tree, every untracked file as pure additions, and deleted or relocated test and snapshot files by name.
Prose and generated/vendored files are skipped. Deleting product code is not a gate change and is not listed.
Tags:
  RH-1  test removed or disabled      RH-3  snapshot/golden changed without its owner file
  RH-4  placeholder in product code   RH-12 CI/test env sniffing in product code
  RH-13 lint/type suppression added   RH-14 CI or hook bypass added (incl. [skip ci] in a commit)
  RH-15 gate value relaxed in a test/CI/config file   RH-16 swallowed exception in product code
Usage: gate-scan.py <base-ref> [--json]
Exit 0: scanned (first line GATE_SUMMARY). Exit 2: GATE_ERROR=<kind>; the caller reports UNAVAILABLE, never "none".
"""
import collections, json, os, re, subprocess, sys

UP_KEYS = r"timeout|retries|retry|tolerance|epsilon|delta|maxdiff|jitter"
DOWN_KEYS = r"threshold|min_score|minimum|coverage|required"
PAT = {
    "test_decl": re.compile(r"^\s*(?:(?:it|test|describe|context|specify)(?:\.\w+)?\s*\(|def test_\w+|func Test\w+\(|#\[test\]|@Test\b|func test\w+\(\)|(?:it|describe|context)\s+['\"])"),
    "skip": re.compile(r"\b(?:it|test|describe)\.(?:skip|only)\s*\(|\b(?:xit|xdescribe|xtest|fit|fdescribe)\s*\(|@pytest\.mark\.skip|pytest\.skip\(|#\[ignore|\bt\.Skip\w*\(|@Disabled\b|@Ignore\b|XCTSkip|@tag :skip"),
    "skip_test_only": re.compile(r"^\s*(?:skip|pending)\s*(?:$|[('\"])"),
    "placeholder": re.compile(r"todo!\(\)|unimplemented!\(\)|NotImplementedError|(?:throw|raise|Error\()[^\n]*not implemented|^\s*pass\s*#\s*TODO", re.I),
    "env": re.compile(r"process\.env\.CI\b|NODE_ENV\s*===?\s*['\"]test['\"]|RAILS_ENV|Rails\.env\.test\?|PYTEST_CURRENT_TEST|GITHUB_ACTIONS"),
    "suppress": re.compile(r"eslint-disable|@ts-ignore|@ts-expect-error|#\s*type:\s*ignore|#\s*noqa|#\[allow\(|//\s*nolint|rubocop:disable|@SuppressWarnings|biome-ignore|#\s*pragma:\s*no cover|/\*\s*istanbul ignore"),
    "bypass": re.compile(r"continue-on-error:\s*true|allow_failure:\s*true|--no-verify\b(?!-)|\[skip ci\]|\[ci skip\]", re.I),
    "num_key": re.compile(r"\b([A-Za-z_]*?(?:" + UP_KEYS + "|" + DOWN_KEYS + r"))\b\W{0,6}?(\d+(?:\.\d+)?)", re.I),
    "timer": re.compile(r"(?:set|clear)(?:Timeout|Interval)"),
    "exact_assert": re.compile(r"\.(?:toBe|toEqual|toStrictEqual|toHaveLength)\(\s*-?\d|assertEqual\("),
    "bound_assert": re.compile(r"\.(?:toBeGreaterThan|toBeGreaterThanOrEqual|toBeLessThan|toBeLessThanOrEqual)\(|assert(?:Greater|Less)\w*\("),
    "swallow": re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}|except[^:\n]*:\s*pass\b|rescue\s+nil\b|\b_\s*=\s*err\b"),
    "catch_open": re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*$"),
    "except_open": re.compile(r"^\s*except\b[^:]*:\s*$"),
}
PROSE_EXT = {".md", ".mdx", ".txt", ".rst", ".adoc"}
LOCKFILES = {"package-lock.json", "bun.lock", "bun.lockb", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock", "Gemfile.lock"}
CI_PATHS = re.compile(r"(^|/)(\.github/workflows/|\.gitlab/ci/|\.circleci/|\.gitlab-ci\.yml$|jenkinsfile$|\.travis\.yml$|azure-pipelines\.yml$|bitbucket-pipelines\.yml$)", re.I)
CONFIG_BASE = {"pytest.ini", "tox.ini", "bunfig.toml", "codecov.yml", ".codecov.yml", ".pre-commit-config.yaml", "lefthook.yml", "mypy.ini", ".flake8", "ruff.toml", "biome.json", "setup.cfg", "package.json", "pyproject.toml"}
CONFIG_PREFIX = ("vitest.config", "jest.config", ".eslintrc", "eslint.config", "tsconfig", ".golangci", "playwright.config", "cypress.config", ".prettierrc")
TEST_BASE = re.compile(r"[._](?:test|spec)\.|^test_.*\.py$|Tests?\.(?:java|kt|scala)$|Tests\.swift$|_test\.go$|_test\.exs$")


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout


def classify(path):
    base = os.path.basename(path)
    parts = path.split("/")
    ext = os.path.splitext(base)[1].lower()
    if ext in PROSE_EXT:
        return "prose"
    if base in LOCKFILES or base.endswith((".min.js", ".min.css")) or any(p in ("dist", "build", "vendor", "node_modules") for p in parts[:-1]):
        return "generated"
    if "__snapshots__" in parts or ext == ".snap":
        return "snapshot"
    if ext == ".golden" or "testdata" in parts:
        return "golden"
    if CI_PATHS.search(path):
        return "ci"
    if base in CONFIG_BASE or base.startswith(CONFIG_PREFIX):
        return "config"
    if any(p in ("test", "tests", "__tests__", "spec") for p in parts[:-1]) or TEST_BASE.search(base):
        return "test"
    return "product"


def parse_diff(text):
    """Yield (path, hunks) where a hunk is {'added': [(line, text)], 'removed': [(line, text)]}."""
    files, path, hunk, new_ln, old_ln = collections.OrderedDict(), None, None, 0, 0
    for raw in text.split("\n"):
        if raw.startswith("diff --git"):
            path, hunk = None, None
        elif raw.startswith("+++ "):
            p = raw[4:].strip()
            p = p[2:] if p.startswith("b/") else p
            if p.startswith('"') and p.endswith('"'):
                p = p[1:-1]
            path = None if p == "/dev/null" else p
            if path is not None:
                files.setdefault(path, [])
        elif raw.startswith("@@") and path is not None:
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            old_ln, new_ln = int(m.group(1)), int(m.group(2))
            hunk = {"added": [], "removed": []}
            files[path].append(hunk)
        elif hunk is not None and raw.startswith("+"):
            hunk["added"].append((new_ln, raw[1:]))
            new_ln += 1
        elif hunk is not None and raw.startswith("-"):
            hunk["removed"].append((old_ln, raw[1:]))
            old_ln += 1
        elif hunk is not None and raw.startswith(" "):
            new_ln += 1
            old_ln += 1
    return files


def relaxed(hunk):
    """RH-15: a numeric gate value moved in the relaxing direction, or an exact assertion became a bound."""
    hits = []
    old = collections.defaultdict(list)
    for _, t in hunk["removed"]:
        if PAT["timer"].search(t):
            continue
        for k, v in PAT["num_key"].findall(t):
            old[k.lower()].append(float(v))
    for ln, t in hunk["added"]:
        if PAT["timer"].search(t):
            continue
        for k, v in PAT["num_key"].findall(t):
            k, v = k.lower(), float(v)
            if k not in old:
                continue
            up = re.search(r"(?:" + UP_KEYS + r")$", k, re.I) is not None
            if any((v > o) if up else (v < o) for o in old[k]):
                hits.append((ln, t, f"{k} {min(old[k]) if up else max(old[k]):g} -> {v:g}"))
    if any(PAT["exact_assert"].search(t) for _, t in hunk["removed"]):
        for ln, t in hunk["added"]:
            if PAT["bound_assert"].search(t):
                hits.append((ln, t, "exact assertion -> bound"))
    return hits


def scan(repo, base):
    code, mb = git("merge-base", base, "HEAD", cwd=repo)
    if code != 0:
        code, mb = git("merge-base", f"origin/{base}", "HEAD", cwd=repo)
    if code != 0:
        return None, f"GATE_ERROR=no_base ref={base} fix=git fetch origin {base}"
    mb = mb.strip()
    code, diff = git("diff", "-M", "--no-ext-diff", "--no-textconv", "-U0", mb, cwd=repo)
    if code != 0:
        return None, "GATE_ERROR=internal step=diff"
    files = parse_diff(diff)
    _, untracked = git("ls-files", "--others", "--exclude-standard", "-z", cwd=repo)
    n_untracked = 0
    for p in filter(None, untracked.split("\0")):
        full = os.path.join(repo, p)
        try:
            if os.path.getsize(full) > 200_000:
                continue
            with open(full, "rb") as fh:
                data = fh.read()
            if b"\0" in data:
                continue
            lines = data.decode("utf-8", "replace").split("\n")
        except OSError:
            continue
        files[p] = [{"added": list(enumerate(lines, 1)), "removed": []}]
        n_untracked += 1
    _, log = git("log", f"{mb}..HEAD", "--format=%h %s%n%b", cwd=repo)
    # deleted files and pure renames carry no +++ line, so the hunk parser never sees them; a lost or relocated test is the case that matters
    _, ns = git("diff", "--name-status", "-M", mb, cwd=repo)
    gone = []  # (old path, new path or None) for deleted test/snapshot files and tests renamed out of the test path
    for row in ns.split("\n"):
        cols = row.split("\t")
        st = cols[0][:1]
        if st == "D" and len(cols) > 1 and classify(cols[1]) in ("test", "snapshot", "golden"):
            gone.append((cols[1], None))
        elif st == "R" and len(cols) > 2 and classify(cols[1]) == "test" and classify(cols[2]) != "test":
            gone.append((cols[1], cols[2]))

    findings, skipped, n_hunks = [], 0, 0
    kinds = {p: classify(p) for p in files}
    owners = [p for p in files if kinds[p] not in ("snapshot", "golden")]
    changed_names = {os.path.basename(p) for p in owners}
    changed_stems = {os.path.basename(p).split(".")[0] for p in owners}

    def add(tag, path, ln, text, note=""):
        findings.append({"tag": tag, "path": path, "line": ln, "text": text.strip()[:160], "note": note})

    for path, hunks in files.items():
        kind = kinds[path]
        n_hunks += len(hunks)
        if kind in ("prose", "generated"):
            skipped += 1
            continue
        is_test, is_gate = kind == "test", kind in ("test", "ci", "config", "snapshot", "golden")
        is_product = kind == "product"
        if kind in ("snapshot", "golden"):
            base_name = os.path.basename(path)
            owner = base_name[:-5] if base_name.endswith(".snap") else base_name
            stem = owner.split(".")[0]
            if owner not in changed_names and stem not in changed_stems:
                add("RH-3" if kind == "snapshot" else "RH-3?", path, hunks[0]["added"][0][0] if hunks and hunks[0]["added"] else 0, "", f"{kind} changed, owner {owner} not in diff")
            continue
        decl_removed = decl_added = 0
        for h in hunks:
            if is_test:
                decl_removed += sum(1 for _, t in h["removed"] if PAT["test_decl"].search(t))
                decl_added += sum(1 for _, t in h["added"] if PAT["test_decl"].search(t))
            added = h["added"]
            for i, (ln, t) in enumerate(added):
                if is_test and (PAT["skip"].search(t) or PAT["skip_test_only"].search(t)):
                    add("RH-1", path, ln, t, "skip idiom added")
                if PAT["suppress"].search(t):
                    add("RH-13", path, ln, t)
                if PAT["bypass"].search(t):
                    add("RH-14", path, ln, t)
                if is_product:
                    if PAT["placeholder"].search(t):
                        add("RH-4", path, ln, t)
                    if PAT["env"].search(t):
                        add("RH-12", path, ln, t)
                    nxt = added[i + 1][1] if i + 1 < len(added) and added[i + 1][0] == ln + 1 else None
                    if PAT["swallow"].search(t) or (nxt is not None and ((PAT["catch_open"].search(t) and re.match(r"^\s*\}", nxt)) or (PAT["except_open"].search(t) and re.match(r"^\s*pass\b", nxt)))):
                        add("RH-16", path, ln, t)
            if is_gate:
                for ln, t, note in relaxed(h):
                    add("RH-15", path, ln, t, note)
        if is_test and decl_removed > decl_added:
            add("RH-1", path, 0, "", f"removed {decl_removed} test declarations, added {decl_added}")
    for old, new in gone:
        if classify(old) == "test":
            _, blob = git("show", f"{mb}:{old}", cwd=repo)
            n = sum(1 for l in blob.split("\n") if PAT["test_decl"].search(l))
            add("RH-1", old, 0, "", f"test file moved to {new}, outside any test path" if new else f"test file deleted, {n} declarations")
        else:
            add("RH-3", old, 0, "", f"{classify(old)} deleted")
    for line in log.split("\n"):
        if PAT["bypass"].search(line) and ("skip ci" in line.lower() or "ci skip" in line.lower()):
            add("RH-14", "<commit>", 0, line, "skip-ci marker in commit message")
    return {"base": mb[:12], "files": len(files), "hunks": n_hunks, "untracked": n_untracked, "deleted": len(gone), "skipped": skipped, "findings": findings}, None


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__.strip())
        return 2
    repo = os.getcwd()
    code, top = git("rev-parse", "--show-toplevel", cwd=repo)
    if code != 0:
        print("GATE_ERROR=not_a_repo")
        return 2
    result, err = scan(top.strip(), args[0])
    if err:
        print(err)
        return 2
    counts = collections.Counter(f["tag"] for f in result["findings"])
    tagged = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items())) if counts else ""
    print(f"GATE_SUMMARY: base={result['base']} files={result['files']} hunks={result['hunks']} untracked={result['untracked']} deleted={result['deleted']} skipped={result['skipped']} tagged={{{tagged}}}")
    if "--json" in argv:
        for f in result["findings"]:
            print(json.dumps(f))
    elif not result["findings"]:
        print("No gate changes tagged.")
    else:
        for f in sorted(result["findings"], key=lambda f: (f["path"], f["line"])):
            loc = f["path"] + (f":{f['line']}" if f["line"] else "")
            extra = f"  ({f['note']})" if f["note"] else ""
            body = f"  + {f['text']}" if f["text"] else ""
            print(f"{f['tag']:<6} {loc}{body}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
