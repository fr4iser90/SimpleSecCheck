"""
Wait for security-summary.html before starting the report web server.
Python replacement for scripts/wait-for-results.sh
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


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
        web_cmd = shlex.split(args.web_cmd)
        return subprocess.call(web_cmd)

    print("Timeout waiting for results")
    return 1


if __name__ == "__main__":
    sys.exit(main())