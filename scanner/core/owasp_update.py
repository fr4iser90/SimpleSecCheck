"""
OWASP Dependency Check Database Update Utility
Python replacement for scripts/update-owasp-db.sh
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def log(message: str, level: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def find_latest_db_age_days(data_dir: Path) -> str:
    if not data_dir.exists() or not any(data_dir.iterdir()):
        return "not_found"

    candidates = list(data_dir.rglob("*.mv.db")) + list(data_dir.rglob("*.h2.db")) + list(data_dir.rglob("*.lock"))
    if not candidates:
        candidates = [p for p in data_dir.rglob("*") if p.is_file()]
    if not candidates:
        return "unknown"

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    age_seconds = max(0, int(datetime.now().timestamp() - latest.stat().st_mtime))
    return str(age_seconds // 86400)


def run_update(
    data_dir: Path,
    log_file: Path,
    docker_image: str,
    nvd_api_key: str | None,
) -> int:
    if shutil.which("docker") is None:
        log("Docker is not installed or not in PATH", "ERROR")
        return 1

    if subprocess.run(["docker", "image", "inspect", docker_image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        log(f"Docker image not found locally, pulling {docker_image}...")
        if subprocess.run(["docker", "pull", docker_image]).returncode != 0:
            log(f"Failed to pull Docker image: {docker_image}", "ERROR")
            return 1

    nvd_flag = []
    if nvd_api_key:
        log("Using NVD_API_KEY for faster updates...")
        nvd_flag = [f"--nvdApiKey={nvd_api_key}"]
    else:
        log("No NVD_API_KEY provided, using public rate limits (slower)...", "WARNING")

    data_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{data_dir}:/SimpleSecCheck/owasp-dependency-check-data",
        "-e",
        f"NVD_API_KEY={nvd_api_key or ''}",
        docker_image,
        "dependency-check",
        "--updateonly",
        "--data",
        "/SimpleSecCheck/owasp-dependency-check-data",
        *nvd_flag,
    ]

    log("Starting database update...")
    log("OWASP Dependency Check will only download changed data (incremental update)")

    with log_file.open("w", encoding="utf-8") as log_f:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if process.stdout is None:
            log("Failed to capture process output", "ERROR")
            return 1
        for line in process.stdout:
            print(line.rstrip())
            log_f.write(line)
        return_code = process.wait()

    if return_code == 0:
        log("Database update completed successfully!", "SUCCESS")
    else:
        log(f"Update completed with warnings or errors (exit code: {return_code})", "WARNING")
        log(f"Check log file for details: {log_file}")
    return return_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Update OWASP Dependency Check vulnerability database")
    parser.add_argument("--data-dir", default=os.getenv("OWASP_DC_DATA_DIR"), help="Path to OWASP data directory")
    parser.add_argument("--log-file", default=os.getenv("LOG_FILE"), help="Path to log file")
    parser.add_argument("--docker-image", default=os.getenv("DOCKER_IMAGE", "fr4iser/simpleseccheck:latest"), help="Docker image")
    parser.add_argument("--nvd-api-key", default=os.getenv("NVD_API_KEY"), help="NVD API key")

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    data_dir = Path(args.data_dir) if args.data_dir else project_root / "scanner" / "data" / "owasp-dependency-check-data"
    log_file = Path(args.log_file) if args.log_file else project_root / "logs" / "owasp-update.log"

    age_status = find_latest_db_age_days(data_dir)
    log(f"Data Directory: {data_dir}")
    log(f"Docker Image: {args.docker_image}")
    log(f"NVD API Key: {'Provided' if args.nvd_api_key else 'Not provided'}")

    if age_status == "not_found":
        log("Database Status: Not found (will be created)", "WARNING")
    elif age_status == "unknown":
        log("Database Status: Found (age unknown)", "WARNING")
    else:
        days = int(age_status)
        if days < 1:
            log("Database Status: Up to date (less than 1 day old)")
        elif days < 7:
            log(f"Database Status: Recent ({days} days old)")
        elif days < 30:
            log(f"Database Status: Moderate ({days} days old)", "WARNING")
        else:
            log(f"Database Status: Outdated ({days} days old - update recommended)", "WARNING")

    return run_update(data_dir, log_file, args.docker_image, args.nvd_api_key)


if __name__ == "__main__":
    sys.exit(main())