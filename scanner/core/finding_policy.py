#!/usr/bin/env python3
"""Load finding policy from a single JSON file. No tool names, no apply logic - plugins own that."""
import json
import os
import sys


def debug(msg):
    print(f"[finding_policy] {msg}", file=sys.stderr)


def load_policy(policy_path):
    if not policy_path:
        return {}
    if not os.path.exists(policy_path):
        debug(f"Policy file not found: {policy_path}")
        return {}
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        debug(f"Failed to load policy file {policy_path}: {exc}")
        return {}
