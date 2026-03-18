"""
Load exit_codes from a plugin manifest.yaml for runtime logging hints.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def plugin_manifest_path_from_class(scanner_class: type) -> Optional[Path]:
    """scanner.plugins.<plugin>.scanner -> scanner/plugins/<plugin>/manifest.yaml"""
    mod = getattr(scanner_class, "__module__", "") or ""
    parts = mod.split(".")
    if len(parts) < 3 or parts[0] != "scanner" or parts[1] != "plugins":
        return None
    plugin = parts[2]
    root = Path(__file__).resolve().parent.parent
    p = root / "plugins" / plugin / "manifest.yaml"
    return p if p.is_file() else None


@lru_cache(maxsize=64)
def _load_exit_codes_section(manifest_path: str) -> Optional[Dict[str, Any]]:
    try:
        import yaml

        with open(manifest_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    if not data or not isinstance(data, dict):
        return None
    ec = data.get("exit_codes")
    return ec if isinstance(ec, dict) else None


def _basename_matches_binary(cmd0: str, binary: str) -> bool:
    if not binary or not cmd0:
        return True
    b = os.path.basename(cmd0).lower()
    ref = os.path.basename(binary.strip()).lower()
    return b == ref or b.startswith(ref + ".") or ref == b.split(".")[0]


def lookup_exit_description(
    manifest_path: Path, cmd: List[str], returncode: int
) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Returns (description_for_code, manifest_note, has_codes_dict).
    If binary filter excludes this cmd, returns (None, None, False).
    """
    section = _load_exit_codes_section(str(manifest_path.resolve()))
    if not section:
        return None, None, False
    binary = section.get("binary")
    if binary and cmd:
        if not _basename_matches_binary(cmd[0], str(binary)):
            return None, None, False
    codes = section.get("codes")
    if not isinstance(codes, dict):
        codes = {}
    has_codes = len(codes) > 0
    desc = codes.get(returncode)
    if desc is None:
        desc = codes.get(str(returncode))
    note = section.get("note")
    if isinstance(note, str):
        n = note.strip() or None
    else:
        n = None
    if desc is not None and isinstance(desc, str):
        d = desc.strip() or None
        return d, n, has_codes
    return None, n, has_codes
