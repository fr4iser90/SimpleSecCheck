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


def _policy_path_regex_variants(regex):
    """
    Expand legacy policy patterns for repo-root-relative scanner paths.

    Patterns like ``.*/backend/foo.py`` fail on ``backend/foo.py`` because greedy
    ``.*`` consumes the first path segment before the required ``/`` (e.g. it eats
    ``backend`` and then cannot match ``/Dockerfile``). Accept both anchored and
    nested forms.
    """
    s = str(regex)
    variants = [s]
    if s.startswith(".*/"):
        variants.append("(?:^|.*/)" + s[3:])
    return variants


def matches_path_for_policy(path, regex):
    if regex is None:
        return True
    if path is None:
        path = ""
    candidates = [str(path)]
    normalized = normalize_policy_path(path)
    if normalized != candidates[0]:
        candidates.append(normalized)
    patterns = _policy_path_regex_variants(regex)
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error:
            return False
    return any(pat.search(c) is not None for pat in compiled for c in candidates)
