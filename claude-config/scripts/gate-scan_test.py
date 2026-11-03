#!/usr/bin/env python3
"""Self-test for gate-scan.py: builds a temp git repo, weakens gates on a branch, checks every tag fires once and the decoys stay quiet.
Usage: python3 gate-scan_test.py"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "gate-scan.py")


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def write(repo, rel, text):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(text)


def run_scan(repo, base):
    r = subprocess.run([sys.executable, SCAN, base], cwd=repo, capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    tmp = tempfile.mkdtemp(prefix="gate-scan-test-")
    sh(tmp, "git", "init", "-q", "-b", "main")
    sh(tmp, "git", "config", "user.email", "t@example.com")
    sh(tmp, "git", "config", "user.name", "t")
    write(tmp, "src/a.ts", "export function a() {\n  return 1;\n}\n// eslint-disable-next-line no-console  (pre-existing, must not be tagged)\nconsole.log(a());\n")
    write(tmp, "src/b.ts", "export const b = 2;\n")
    write(tmp, "test/a.test.ts", "it('one', () => {\n  expect(a()).toBe(1);\n});\nit('two', () => {\n  expect(a()).toBe(1);\n});\nit('three', () => {\n  expect(a()).toBe(1);\n});\n")
    write(tmp, "test/__snapshots__/a.test.ts.snap", "exports[`one`] = `1`;\n")
    write(tmp, "test/b.test.ts", "it('b1', () => {});\nit('b2', () => {});\n")
    write(tmp, "vitest.config.ts", "export default { test: { testTimeout: 5000, coverage: { threshold: 80 } } };\n")
    write(tmp, ".github/workflows/ci.yml", "jobs:\n  test:\n    steps:\n      - run: bun test\n")
    write(tmp, "README.md", "docs\n")
    sh(tmp, "git", "add", "-A")
    sh(tmp, "git", "commit", "-qm", "base")
    sh(tmp, "git", "checkout", "-qb", "feature")

    # RH-1 (declaration removed) + RH-1 (skip idiom) + RH-15 (exact -> bound)
    write(tmp, "test/a.test.ts", "it('one', () => {\n  expect(a()).toBeGreaterThan(0);\n});\nit.skip('two', () => {\n  expect(a()).toBe(1);\n});\n")
    # RH-3: snapshot changed, owner a.test.ts IS in diff -> must NOT fire; add an orphan snapshot that must fire
    write(tmp, "test/__snapshots__/a.test.ts.snap", "exports[`one`] = `2`;\n")
    write(tmp, "test/__snapshots__/orphan.test.ts.snap", "exports[`x`] = `y`;\n")
    # RH-13 added suppression, RH-4 placeholder, RH-12 env sniff, RH-16 swallow (one-line + multi-line); decoy: setTimeout in product code
    # decoys in product code: map.fit() is not a focused test, a comment saying "not implemented" is not a placeholder
    write(tmp, "src/a.ts", "export function a() {\n  // @ts-ignore\n  return 1;\n}\n// eslint-disable-next-line no-console  (pre-existing, must not be tagged)\nconsole.log(a());\nexport function c() {\n  if (process.env.CI) return;\n  throw new Error('not implemented');\n}\ntry { a(); } catch (e) {}\ntry { a(); } catch {\n}\nsetTimeout(() => {}, 9000);\nmap.fit();\n// the legacy path is not implemented here on purpose\n")
    # RH-1: a whole test file deleted
    sh(tmp, "git", "rm", "-q", "test/b.test.ts")
    # RH-15 numeric relax (timeout up, threshold down) in config; RH-14 bypass in CI; decoy: --no-verify-jwt is not --no-verify
    write(tmp, "vitest.config.ts", "export default { test: { testTimeout: 30000, coverage: { threshold: 60 } } };\n")
    write(tmp, ".github/workflows/ci.yml", "jobs:\n  test:\n    continue-on-error: true\n    steps:\n      - run: bun test\n      - run: supabase functions deploy fn --no-verify-jwt\n")
    # decoy: suppression text inside prose must be skipped
    write(tmp, "README.md", "docs\nUse eslint-disable sparingly.\n")
    sh(tmp, "git", "add", "-A")
    sh(tmp, "git", "commit", "-qm", "weaken gates [skip ci]")
    # untracked product file with a swallowed exception (RH-16) must be scanned too
    write(tmp, "src/new.py", "try:\n    x = 1\nexcept Exception:\n    pass\n")

    code, out = run_scan(tmp, "main")
    print(out)
    assert code == 0, f"exit {code}"
    lines = out.strip().split("\n")
    assert lines[0].startswith("GATE_SUMMARY:"), lines[0]
    assert "skipped=1" in lines[0], "README.md should be skipped as prose"
    assert "untracked=1" in lines[0]

    def has(tag, frag):
        return any(l.startswith(tag) and frag in l for l in lines[1:])

    checks = [
        ("RH-1 ", "removed 2 test declarations, added 1"),  # 'one' is unchanged context under -U0; 'two' is rewritten, 'three' is gone
        ("RH-1 ", "it.skip"),
        ("RH-15", "exact assertion -> bound"),
        ("RH-3 ", "orphan.test.ts.snap"),
        ("RH-13", "src/a.ts:2"),
        ("RH-4 ", "not implemented"),
        ("RH-12", "process.env.CI"),
        ("RH-16", "src/a.ts:11"),
        ("RH-16", "src/a.ts:12"),
        ("RH-16", "src/new.py:3"),
        ("RH-15", "testtimeout 5000 -> 30000"),
        ("RH-15", "threshold 80 -> 60"),
        ("RH-14", "continue-on-error"),
        ("RH-14", "skip-ci marker in commit message"),
        ("RH-1 ", "test/b.test.ts  (test file deleted, 2 declarations)"),
    ]
    failed = [c for c in checks if not has(*c)]
    decoys = [
        ("pre-existing", "unchanged eslint-disable line was tagged"),
        ("a.test.ts.snap", "snapshot whose owner is in the diff was tagged"),
        ("setTimeout", "setTimeout counted as a timeout relaxation"),
        ("README.md", "prose file was tagged"),
        ("map.fit", "a product-code fit() call was tagged as a focused test"),
        ("no-verify-jwt", "--no-verify-jwt was tagged as a hook bypass"),
        ("legacy path", "a comment mentioning 'not implemented' was tagged as a placeholder"),
    ]
    tripped = [why for frag, why in decoys if any(frag in l for l in lines[1:])]
    code2, out2 = run_scan(tmp, "no-such-ref")
    assert code2 == 2 and out2.startswith("GATE_ERROR=no_base"), out2
    shutil.rmtree(tmp, ignore_errors=True)
    if failed or tripped:
        for c in failed:
            print("MISSING:", c)
        for t in tripped:
            print("DECOY TRIPPED:", t)
        sys.exit(1)
    print(f"OK: {len(checks)} tags fired, {len(decoys)} decoys quiet, no_base exits 2")


if __name__ == "__main__":
    main()
