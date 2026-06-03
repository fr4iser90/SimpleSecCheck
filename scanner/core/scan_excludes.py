#!/usr/bin/env python3
"""
Central scan excludes: merges user SIMPLESECCHECK_EXCLUDE_PATHS with the
finding-policy file (one file only). No second default path — uses finding_policy.py.

Orchestrator calls prepare_scan_excludes_env() once before scanners.
Scanners already read SIMPLESECCHECK_EXCLUDE_PATHS at startup.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Union

from scanner.core.finding_policy import (
    ENV_POLICY_FILE,
    ENV_POLICY_IN_CONTAINER,
    publish_finding_policy_path_to_env,
)
from scanner.core.policy_matching import normalize_policy_path

ENV_EXCLUDE_PATHS = "SIMPLESECCHECK_EXCLUDE_PATHS"


def _policy_relative_under_target(target: Path) -> str:
    raw = os.getenv(ENV_POLICY_IN_CONTAINER, "").strip() or os.getenv(ENV_POLICY_FILE, "").strip()
    if not raw:
        return ""
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = target / raw.lstrip("/")
    if not candidate.is_file():
        return ""
    try:
        return str(candidate.resolve().relative_to(target.resolve())).replace("\\", "/")
    except ValueError:
        return normalize_policy_path(str(candidate))


def merged_exclude_list(
    target: Union[str, Path],
    extra_csv: str | None = None,
) -> List[str]:
    target_p = Path(target)
    out: List[str] = []
    rel = _policy_relative_under_target(target_p)
    if rel:
        out.append(rel)
    raw = extra_csv if extra_csv is not None else os.getenv(ENV_EXCLUDE_PATHS, "")
    for part in raw.split(","):
        p = part.strip()
        if p and p not in out:
            out.append(p)
    return out


def prepare_scan_excludes_env(target: Union[str, Path]) -> str:
    """
    Once per scan: resolve policy path, publish env, merge into SIMPLESECCHECK_EXCLUDE_PATHS.
    Returns the merged comma-separated string.
    """
    target_p = Path(target)
    publish_finding_policy_path_to_env(target_p)
    user_csv = os.getenv(ENV_EXCLUDE_PATHS, "")
    merged = ",".join(merged_exclude_list(target_p, extra_csv=user_csv))
    os.environ[ENV_EXCLUDE_PATHS] = merged
    return merged


def path_matches_exclude(target: Union[str, Path], candidate: Union[str, Path]) -> bool:
    target_p = Path(target)
    try:
        rel = normalize_policy_path(
            str(Path(candidate).resolve().relative_to(target_p.resolve()))
        )
    except ValueError:
        rel = normalize_policy_path(str(candidate))
    for pattern in merged_exclude_list(target_p):
        pat = normalize_policy_path(pattern)
        if rel == pat:
            return True
        if pat in rel or pat in str(candidate):
            return True
    return False


def bandit_extra_argv(target: Union[str, Path]) -> List[str]:
    argv: List[str] = []
    target_p = Path(target)
    for pattern in merged_exclude_list(target_p):
        candidate = target_p / pattern
        if candidate.is_file() or candidate.is_dir():
            argv.extend(["-x", str(candidate.resolve())])
    return argv


def detect_secrets_exclude_argv(exclude_csv: str) -> List[str]:
    argv: List[str] = []
    for path in exclude_csv.split(","):
        p = path.strip()
        if not p:
            continue
        escaped = re.escape(p)
        if "/" in p or "." in Path(p).name:
            argv.extend(["--exclude-files", f".*{escaped}.*"])
        else:
            argv.extend(["--exclude-files", f".*/{escaped}/.*"])
    return argv


def owasp_exclude_argv(exclude_csv: str) -> List[str]:
    argv: List[str] = []
    for path in exclude_csv.split(","):
        p = path.strip()
        if not p:
            continue
        if "/" in p or p.endswith((".json", ".xml", ".yaml", ".yml", ".html")):
            argv.extend(["--exclude", p])
        else:
            argv.extend(["--exclude", f"**/{p}/**"])
    return argv


def semgrep_exclude_argv(exclude_csv: str) -> List[str]:
    argv: List[str] = []
    for path in exclude_csv.split(","):
        p = path.strip()
        if p:
            argv.extend(["--exclude", p])
    return argv


def trivy_skip_argv(exclude_csv: str) -> List[str]:
    """Trivy: files vs directories from the same central list."""
    argv: List[str] = []
    for path in exclude_csv.split(","):
        p = path.strip()
        if not p:
            continue
        if "/" in p or "." in Path(p).name:
            argv.extend(["--skip-files", f"**/{p}"])
        else:
            argv.extend(["--skip-dirs", f"*/{p}"])
    return argv
