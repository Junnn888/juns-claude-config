"""Running `claude -p` sessions for the eval runners. Needs evals/rules on sys.path for `judge`."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

from judge import result_event

CONFIG_FILE_GLOBS = ["CLAUDE.md", "settings.json", "output-styles/*.md", "agents/*.md", "commands/*.md"]


def child_env(config_dir):
    # Drop the parent session's variables so each child starts like a fresh terminal session.
    env = {k: v for k, v in os.environ.items() if not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_") or k in ("CLAUDE_PID", "CLAUDE_EFFORT"))}
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env


def resolved_config_dir(config_dir):
    return Path(config_dir or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()


def config_hash(config_dir):
    digest = hashlib.sha256()
    files = sorted({p for pattern in CONFIG_FILE_GLOBS for p in config_dir.glob(pattern) if p.is_file()})
    for path in files:
        digest.update(str(path.relative_to(config_dir)).encode() + b"\0" + path.read_bytes() + b"\0")
    return {"sha256": digest.hexdigest(), "files": len(files)}


def command_output(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def tested_block(first_session, config_dir):
    return {
        "claude_version": command_output(["claude", "--version"]),
        "model": first_session.get("model"),
        "permission_mode": first_session.get("permissionMode"),
        "output_style": first_session.get("output_style"),
        "config_dir": str(config_dir).replace(str(Path.home()), "~", 1),
        "config_hash": config_hash(config_dir),
    }


def parse_stream(text):
    events = []
    for line in text.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def run_turn(prompt, session_id, project, env, max_budget_usd=3, timeout_seconds=600):
    command = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-budget-usd", str(max_budget_usd)]
    if session_id:
        command += ["--resume", session_id]
    try:
        proc = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as timeout:
        partial = timeout.stdout.decode(errors="replace") if isinstance(timeout.stdout, bytes) else (timeout.stdout or "")
        return partial, f"timed out after {timeout_seconds}s"
    events = parse_stream(proc.stdout)
    result = result_event(events)
    if result is None:
        return proc.stdout, f"exit {proc.returncode}, no result event: {proc.stderr.strip()[-200:]}"
    if result.get("is_error"):
        return proc.stdout, f"session ended with an error: {str(result.get('result'))[:200]}"
    return proc.stdout, None
