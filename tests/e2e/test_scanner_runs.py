"""
E2E: Scanner runs with and without finding policy.
Runs docker scanner once without policy, once with .scanning/finding-policy.json.
Logs what each tool does (orchestrator output).
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
LOG_DIR = RESULTS_DIR / "test-logs"
POLICY_FILE = REPO_ROOT / ".scanning" / "finding-policy.json"

# Default scan target (override with env SCAN_TARGET)
SCAN_TARGET = os.environ.get("SCAN_TARGET", "https://github.com/fr4iser90/SimpleSecCheck")
GIT_BRANCH = os.environ.get("GIT_BRANCH", "main")

# Match orchestrator lines to see what each tool does
ORCH_LINE = re.compile(
    r"\[SimpleSecCheck Orchestrator\].*"
    r"(?:--- Orchestrating (\w+) Scan ---|(\w+) completed|(\w+) failed|Using Python scanner)"
)
TOOL_LINE = re.compile(r"^\[([^\]]+)\]\s+(.+)", re.MULTILINE)


def run_scanner(finding_policy_path: str | None, log_path: Path) -> tuple[int, str]:
    """Run scanner container. Returns (returncode, combined stdout+stderr)."""
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{RESULTS_DIR}:/app/results",
        "-e", "SCAN_TYPE=code",
        "-e", "TARGET_TYPE=git_repo",
        "-e", f"SCAN_TARGET={SCAN_TARGET}",
        "-e", f"GIT_BRANCH={GIT_BRANCH}",
        "-e", "COLLECT_METADATA=true",
    ]
    if finding_policy_path:
        # Mount policy into container and set env
        policy_host = REPO_ROOT / ".scanning" / "finding-policy.json"
        if not policy_host.exists():
            pytest.skip(".scanning/finding-policy.json not found")
        cmd.extend([
            "-v", f"{policy_host}:{finding_policy_path}:ro",
            "-e", f"FINDING_POLICY_FILE_IN_CONTAINER={finding_policy_path}",
        ])
    cmd.extend([
        "simpleseccheck-scanner:local",
        "python3", "-m", "scanner.core.orchestrator",
    ])
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
        out = proc.stdout or ""
        f.write(out)
    return proc.returncode, out


def extract_tool_events(output: str) -> list[dict]:
    """Extract per-tool events from orchestrator output (quiet or SSC_SCAN_LOG_VERBOSE)."""
    events = []
    for line in output.splitlines():
        if "--- Orchestrating" in line:
            m = re.search(r"--- Orchestrating (\w+) Scan ---", line)
            if m:
                events.append({"tool": m.group(1), "event": "start"})
        elif "[Tool]" in line and " start timeout=" in line:
            m = re.search(r"\[Tool\] (.+?) start timeout=", line)
            if m:
                events.append({"tool": m.group(1).strip(), "event": "start"})
        elif "completed successfully" in line or "completed successfully (" in line:
            m = re.search(r"\(1\) (\w+) completed successfully", line)
            if m:
                events.append({"tool": m.group(1), "event": "completed"})
        elif re.search(r"\[Tool\] .+ OK\s*$", line):
            m = re.search(r"\[Tool\] (.+?) OK\s*$", line)
            if m:
                events.append({"tool": m.group(1).strip(), "event": "completed"})
        elif "ORCHESTRATOR WARNING" in line and "failed" in line:
            m = re.search(r"\(1\) \[ORCHESTRATOR WARNING\] (\w+) failed", line)
            if m:
                events.append({"tool": m.group(1), "event": "failed"})
        elif "[Tool]" in line and "FAILED (continuing)" in line:
            m = re.search(r"\[Tool\] (.+?) FAILED \(continuing\)", line)
            if m:
                events.append({"tool": m.group(1).strip(), "event": "failed"})
    return events


@pytest.mark.e2e
def test_scanner_run_without_finding_policy():
    """Run scanner without finding policy; log what each tool does."""
    log_path = LOG_DIR / "scan-without-policy.log"
    code, out = run_scanner(finding_policy_path=None, log_path=log_path)
    events = extract_tool_events(out)
    assert len(events) >= 1, "Expected at least one tool event; check log"
    # Log summary
    tools_started = [e["tool"] for e in events if e["event"] == "start"]
    tools_ok = [e["tool"] for e in events if e["event"] == "completed"]
    tools_failed = [e["tool"] for e in events if e["event"] == "failed"]
    print(f"\n[WITHOUT POLICY] Tools started: {len(tools_started)}")
    print(f"  Completed: {tools_ok}")
    print(f"  Failed: {tools_failed}")
    print(f"  Full log: {log_path}")
    # Allow non-zero (some tools may fail in CI)
    assert code in (0, 1), f"Unexpected exit code {code}"


@pytest.mark.e2e
def test_scanner_run_with_finding_policy():
    """Run scanner with finding policy mounted at /.scanning/finding-policy.json."""
    if not POLICY_FILE.exists():
        pytest.skip("No .scanning/finding-policy.json")
    log_path = LOG_DIR / "scan-with-policy.log"
    code, out = run_scanner(
        finding_policy_path="/.scanning/finding-policy.json",
        log_path=log_path,
    )
    events = extract_tool_events(out)
    assert len(events) >= 1, "Expected at least one tool event; check log"
    tools_started = [e["tool"] for e in events if e["event"] == "start"]
    tools_ok = [e["tool"] for e in events if e["event"] == "completed"]
    tools_failed = [e["tool"] for e in events if e["event"] == "failed"]
    print(f"\n[WITH POLICY] Tools started: {len(tools_started)}")
    print(f"  Completed: {tools_ok}")
    print(f"  Failed: {tools_failed}")
    print(f"  Full log: {log_path}")
    assert code in (0, 1), f"Unexpected exit code {code}"
