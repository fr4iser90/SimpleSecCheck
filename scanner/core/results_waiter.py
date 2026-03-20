"""
Wait for security-summary.html before starting the report web server.
Python replacement for scripts/wait-for-results.sh
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

_SAFE_ARG = re.compile(r"^[\w.\-/:~]+$")
_ALLOWED_EXE = frozenset({"python", "python3"})


def _validated_web_argv(web_cmd: str) -> list[str] | None:
    """Build argv for subprocess (no shell); reject obvious injection / -c payloads."""
    try:
        argv = shlex.split(web_cmd, posix=True)
    except ValueError:
        return None
    if not argv:
        return None
    if Path(argv[0]).name not in _ALLOWED_EXE:
        return None
    if "-c" in argv:
        return None
    for part in argv:
        if not _SAFE_ARG.fullmatch(part):
            return None
    return argv


def wait_for_results(results_file: Path, timeout: int) -> bool:
    for _ in range(timeout):
        if results_file.exists():
            return True
        time.sleep(1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for scan results then start web server")
    parser.add_argument("--results-file", default=os.getenv("RESULT_FILE", "/results/security-summary.html"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("TIMEOUT", "300")))
    parser.add_argument("--web-cmd", default=os.getenv("WEB_CMD", "python3 web/app.py"))

    args = parser.parse_args()
    results_file = Path(args.results_file)

    print(f"Waiting for {results_file} to exist...")
    if wait_for_results(results_file, args.timeout):
        print(f"Found {results_file}, starting web server.")
        web_argv = _validated_web_argv(args.web_cmd)
        if web_argv is None:
            print("Invalid WEB_CMD / --web-cmd: use python3 with script path only (no -c).", file=sys.stderr)
            return 1
        return subprocess.run(web_argv, check=False).returncode

    print("Timeout waiting for results")
    return 1


if __name__ == "__main__":
    sys.exit(main())