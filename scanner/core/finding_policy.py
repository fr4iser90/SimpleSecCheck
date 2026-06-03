#!/usr/bin/env python3
"""Load finding policy from a single JSON file. No tool names, no apply logic - plugins own that."""
import json
import os
import sys

# Conventional path under project root when no path is specified
DEFAULT_POLICY_RELATIVE = ".scanning/finding-policy.json"


def debug(msg):
    print(f"[finding_policy] {msg}", file=sys.stderr)


def _extract_tool_policies(data):
    """Keep only tool blocks (dict values); ignore metadata keys like version, updated."""
    if not isinstance(data, dict):
        return {}
    policies = {}
    skipped = []
    for key, value in data.items():
        if isinstance(value, dict):
            policies[key] = value
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
        return _extract_tool_policies(data)
    except Exception as exc:
        debug(f"Failed to load policy file {policy_path}: {exc}")
        return {}
