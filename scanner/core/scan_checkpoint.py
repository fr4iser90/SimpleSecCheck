"""
Scan checkpoint (results/{scan_id}/checkpoint.json).
Resume skips only for plugins that declare manifest.checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CHECKPOINT_VERSION = 1
STEP_PREFIX = "scanner:"


def scanner_step_key(tools_key: str) -> str:
    return f"{STEP_PREFIX}{tools_key}"


def compute_scan_config_hash(
    *,
    scan_types: List[str],
    target_type: str,
    collect_metadata: bool,
    selected_scanners: Optional[List[str]],
    overrides_json: str,
) -> str:
    payload = {
        "scan_types": sorted(scan_types),
        "target_type": target_type,
        "collect_metadata": collect_metadata,
        "selected": sorted(selected_scanners) if selected_scanners else None,
        "overrides": overrides_json.strip(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def target_fingerprint_git(repo: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def run_tool_version(version_command: Optional[List[str]]) -> str:
    if not version_command:
        return ""
    try:
        r = subprocess.run(
            version_command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        out = (r.stdout or r.stderr or "").strip().splitlines()
        return (out[0] if out else "").strip()[:500]
    except Exception:
        return ""


def artifact_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_primary_artifact(
    scanner_dir: Path,
    primary: str,
    fmt: str,
) -> Tuple[bool, str, str]:
    """
    Returns (ok, artifact_hash, error_reason).
    """
    p = scanner_dir / primary
    if not p.is_file():
        return False, "", "missing"
    if p.stat().st_size == 0:
        return False, "", "empty"
    fmt = (fmt or "json").lower()
    try:
        raw = p.read_bytes()
        if fmt == "json":
            json.loads(raw.decode("utf-8", errors="strict"))
        elif fmt == "sarif":
            data = json.loads(raw.decode("utf-8", errors="strict"))
            if not isinstance(data, dict) or "runs" not in data:
                return False, "", "sarif_shape"
        # any: size only
    except Exception:
        return False, "", "parse"
    return True, artifact_sha256(p), ""


def scanner_config_hash(tools_key: str, timeout_sec: int, override_dict: Dict[str, Any]) -> str:
    # Per-plugin slice only (no secrets — env values in override should be non-secret flags)
    env_slice = {}
    if isinstance(override_dict.get("env"), dict):
        for k, v in override_dict["env"].items():
            env_slice[str(k)] = str(v)
    payload = {
        "tools_key": tools_key,
        "timeout": timeout_sec,
        "env": dict(sorted(env_slice.items())),
        "enabled": override_dict.get("enabled"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_checkpoint(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return _empty_checkpoint()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _empty_checkpoint()
        data.setdefault("version", CHECKPOINT_VERSION)
        data.setdefault("steps", {})
        return data
    except Exception:
        return _empty_checkpoint()


def _empty_checkpoint() -> Dict[str, Any]:
    return {
        "version": CHECKPOINT_VERSION,
        "status": "running",
        "resumed": False,
        "scan_config_hash": "",
        "target_fingerprint": "",
        "steps": {},
        "pipeline_order": [],
    }


def save_checkpoint(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def invalidate_scanner_steps(data: Dict[str, Any]) -> None:
    steps = data.get("steps")
    if not isinstance(steps, dict):
        data["steps"] = {}
        return
    for k in list(steps.keys()):
        if k.startswith(STEP_PREFIX):
            del steps[k]


def can_skip_scanner(
    *,
    cp: Dict[str, Any],
    tools_key: str,
    checkpoint_cfg,
    scanner_dir: Path,
    config_hash: str,
    current_global_hash: str,
    executed_upstream: bool,
) -> Tuple[bool, str]:
    """If executed_upstream, never skip (downstream invalidation)."""
    if executed_upstream:
        return False, "upstream_rerun"
    if not checkpoint_cfg:
        return False, "no_manifest_checkpoint"
    key = scanner_step_key(tools_key)
    steps = cp.get("steps") or {}
    st = steps.get(key)
    if not isinstance(st, dict) or st.get("status") != "completed":
        return False, "not_completed"
    if (st.get("global_config_hash") or "") != current_global_hash:
        return False, "global_hash_mismatch"
    if st.get("config_hash") != config_hash:
        return False, "config_hash_mismatch"
    ver = run_tool_version(checkpoint_cfg.version_command)
    stored_ver = (st.get("tool_version") or "").strip()
    if checkpoint_cfg.version_command and ver != stored_ver:
        return False, "tool_version_mismatch"
    ok, ah, err = validate_primary_artifact(
        scanner_dir,
        checkpoint_cfg.primary_artifact,
        checkpoint_cfg.artifact_format,
    )
    if not ok:
        return False, f"artifact:{err}"
    if st.get("artifact_hash") != ah:
        return False, "artifact_hash_mismatch"
    return True, ""


def record_scanner_completed(
    cp: Dict[str, Any],
    tools_key: str,
    checkpoint_cfg,
    scanner_dir: Path,
    current_global_hash: str,
    config_hash: str,
) -> None:
    if not checkpoint_cfg:
        return
    ok, ah, _ = validate_primary_artifact(
        scanner_dir,
        checkpoint_cfg.primary_artifact,
        checkpoint_cfg.artifact_format,
    )
    if not ok:
        return
    ver = run_tool_version(checkpoint_cfg.version_command)
    key = scanner_step_key(tools_key)
    if "steps" not in cp or not isinstance(cp["steps"], dict):
        cp["steps"] = {}
    cp["steps"][key] = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": ver,
        "config_hash": config_hash,
        "global_config_hash": current_global_hash,
        "artifact_hash": ah,
    }


def checkpoint_resumed_any(cp: Dict[str, Any]) -> bool:
    """True if this run used at least one checkpoint skip (tracked externally)."""
    return bool(cp.get("resumed"))
