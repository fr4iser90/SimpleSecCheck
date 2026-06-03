#!/usr/bin/env python3
"""Load finding policy from a single JSON file. No tool names, no apply logic - plugins own that."""
import json
import os
import sys
from pathlib import Path

# Conventional path under project root when no path is specified (only default in repo)
DEFAULT_POLICY_RELATIVE = ".scanning/finding-policy.json"
ENV_POLICY_IN_CONTAINER = "FINDING_POLICY_FILE_IN_CONTAINER"
ENV_POLICY_FILE = "FINDING_POLICY_FILE"


def default_policy_path_under_target(target_path: str | Path) -> Path:
    target = Path(target_path)
    return target.joinpath(*DEFAULT_POLICY_RELATIVE.split("/"))


def resolve_finding_policy_absolute_path(target_path: str | Path) -> str:
    """User/env path, else default file if it exists. Empty if none."""
    target = Path(target_path)
    for env_key in (ENV_POLICY_IN_CONTAINER, ENV_POLICY_FILE):
        raw = os.getenv(env_key, "").strip()
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = target / raw.lstrip("/")
        if candidate.is_file():
            return str(candidate.resolve())
    default = default_policy_path_under_target(target)
    if default.is_file():
        return str(default.resolve())
    return ""


def publish_finding_policy_path_to_env(target_path: str | Path) -> str:
    """Set FINDING_POLICY_FILE_IN_CONTAINER once per scan (orchestrator calls this)."""
    abs_path = resolve_finding_policy_absolute_path(target_path)
    if abs_path:
        os.environ[ENV_POLICY_IN_CONTAINER] = abs_path
    return abs_path


def debug(msg):
    print(f"[finding_policy] {msg}", file=sys.stderr)


def _extract_tool_policies(data):
    """Keep only tool blocks (dict values); ignore metadata keys like version, updated."""
    if not isinstance(data, dict):
        return {}
    try:
        from scanner.core.policy_schema_registry import resolve_policy_key
    except ImportError:
        resolve_policy_key = None  # type: ignore

    policies = {}
    skipped = []
    for key, value in data.items():
        if isinstance(value, dict):
            store_key = key
            if resolve_policy_key is not None:
                store_key, hint = resolve_policy_key(key)
                if hint:
                    debug(f"Policy alias: {hint}")
                if store_key in policies and store_key != key:
                    debug(f"Policy: merging duplicate block '{key}' into '{store_key}'")
            policies[store_key] = value
        else:
            skipped.append(key)
    if skipped:
        debug(f"Ignoring non-tool top-level keys: {', '.join(skipped)}")
    return policies


def load_policy(policy_path):
    if not policy_path:
        return {}
    if not os.path.exists(policy_path):
        debug(f"Policy file not found: {policy_path}")
        return {}
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            debug(f"Policy root is not a JSON object: {policy_path}")
            return {}
        policies = _extract_tool_policies(data)
        _validate_loaded_policy(policies, policy_path)
        return policies
    except Exception as exc:
        debug(f"Failed to load policy file {policy_path}: {exc}")
        return {}


def _validate_loaded_policy(policies: dict, policy_path: str) -> None:
    """Log validation warnings/errors when a policy file is loaded (non-fatal)."""
    if not policies:
        return
    try:
        from scanner.core.finding_policy_validate import validate_policy_data
    except ImportError:
        return
    result = validate_policy_data(policies)
    for w in result.get("warnings") or []:
        debug(f"Policy warning ({policy_path}): {w}")
    for e in result.get("errors") or []:
        debug(f"Policy error ({policy_path}): {e}")
