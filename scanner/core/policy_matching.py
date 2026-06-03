#!/usr/bin/env python3
import re

_MOUNT_PREFIXES = ("/app/target/", "/target/")


def normalize_policy_path(path):
    raw = (path or "").replace("\\", "/").strip()
    for pref in _MOUNT_PREFIXES:
        if raw.startswith(pref):
            raw = raw[len(pref) :]
            break
    if "/target/" in raw:
        raw = raw.split("/target/", 1)[-1]
    return raw.lstrip("/")


_PATH_KEYS = ("path", "filename", "file", "PkgName")


def normalize_finding_paths(finding):
    """Strip container mount prefixes from path-like fields for display and dedupe grouping."""
    if not isinstance(finding, dict):
        return finding
    out = dict(finding)
    for key in _PATH_KEYS:
        val = out.get(key)
        if val:
            out[key] = normalize_policy_path(str(val))
    return out


def matches_path_for_policy(path, regex):
    if regex is None:
        return True
    if path is None:
        path = ""
    candidates = [str(path)]
    normalized = normalize_policy_path(path)
    if normalized != candidates[0]:
        candidates.append(normalized)
    try:
        pat = re.compile(str(regex))
    except re.error:
        return False
    return any(pat.search(c) is not None for c in candidates)
