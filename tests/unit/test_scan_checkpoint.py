"""Tests for scanner.core.scan_checkpoint (plugin-agnostic resume helpers)."""
import json
from pathlib import Path

import pytest

from scanner.core.scan_checkpoint import (
    artifact_sha256,
    compute_scan_config_hash,
    can_skip_scanner,
    invalidate_scanner_steps,
    load_checkpoint,
    record_scanner_completed,
    scanner_config_hash,
    scanner_step_key,
    validate_primary_artifact,
)
from scanner.core.scanner_assets.models import ScannerCheckpointConfig


def test_compute_scan_config_hash_stable():
    h1 = compute_scan_config_hash(
        scan_types=["code"],
        target_type="git_repo",
        collect_metadata=True,
        selected_scanners=None,
        overrides_json="{}",
    )
    h2 = compute_scan_config_hash(
        scan_types=["code"],
        target_type="git_repo",
        collect_metadata=True,
        selected_scanners=None,
        overrides_json="{}",
    )
    assert h1 == h2
    h3 = compute_scan_config_hash(
        scan_types=["code"],
        target_type="git_repo",
        collect_metadata=False,
        selected_scanners=None,
        overrides_json="{}",
    )
    assert h1 != h3


def test_scanner_step_key():
    assert scanner_step_key("trivy") == "scanner:trivy"


def test_validate_primary_artifact_json(tmp_path: Path):
    d = tmp_path / "tools" / "x"
    d.mkdir(parents=True)
    f = d / "report.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    ok, h, err = validate_primary_artifact(d, "report.json", "json")
    assert ok and not err
    assert h == artifact_sha256(f)


def test_validate_primary_artifact_empty(tmp_path: Path):
    d = tmp_path / "t"
    d.mkdir()
    (d / "report.json").write_text("", encoding="utf-8")
    ok, h, err = validate_primary_artifact(d, "report.json", "json")
    assert not ok and err == "empty"


def test_invalidate_scanner_steps():
    cp = load_checkpoint(Path("/nonexistent"))
    cp["steps"] = {"scanner:a": {"status": "completed"}, "other": {}}
    invalidate_scanner_steps(cp)
    assert "scanner:a" not in cp["steps"]
    assert "other" in cp["steps"]


def test_can_skip_scanner_ok(tmp_path: Path):
    cfg = ScannerCheckpointConfig(
        primary_artifact="report.json",
        artifact_format="json",
        version_command=None,
    )
    d = tmp_path / "semgrep"
    d.mkdir()
    (d / "report.json").write_text('{"r":[]}', encoding="utf-8")
    ah = artifact_sha256(d / "report.json")
    gh = "globalhash111"
    ch = scanner_config_hash("semgrep", 900, {})
    cp = {
        "scan_config_hash": gh,
        "steps": {
            "scanner:semgrep": {
                "status": "completed",
                "global_config_hash": gh,
                "config_hash": ch,
                "tool_version": "",
                "artifact_hash": ah,
            }
        },
    }
    ok, _ = can_skip_scanner(
        cp=cp,
        tools_key="semgrep",
        checkpoint_cfg=cfg,
        scanner_dir=d,
        config_hash=ch,
        current_global_hash=gh,
    )
    assert ok


def test_can_skip_after_notional_upstream_rerun(tmp_path: Path):
    """Skip is allowed even if an earlier scanner re-ran (independent artifacts)."""
    cfg = ScannerCheckpointConfig("report.json", "json", None)
    d = tmp_path / "s"
    d.mkdir()
    (d / "report.json").write_text("{}", encoding="utf-8")
    ah = artifact_sha256(d / "report.json")
    ch = scanner_config_hash("s", 900, {})
    gh = "sameglobal"
    cp = {
        "scan_config_hash": gh,
        "steps": {
            "scanner:s": {
                "status": "completed",
                "global_config_hash": gh,
                "config_hash": ch,
                "tool_version": "",
                "artifact_hash": ah,
            }
        },
    }
    ok, _ = can_skip_scanner(
        cp=cp,
        tools_key="s",
        checkpoint_cfg=cfg,
        scanner_dir=d,
        config_hash=ch,
        current_global_hash=gh,
    )
    assert ok


def test_record_scanner_completed(tmp_path: Path):
    cfg = ScannerCheckpointConfig("report.json", "json", None)
    d = tmp_path / "trivy"
    d.mkdir()
    (d / "report.json").write_text('{"Results":[]}', encoding="utf-8")
    cp = {"steps": {}}
    record_scanner_completed(cp, "trivy", cfg, d, "gh", "ch", target_fingerprint_ok=True)
    assert cp["steps"]["scanner:trivy"]["status"] == "completed"
    assert cp["steps"]["scanner:trivy"]["global_config_hash"] == "gh"


def test_record_scanner_completed_skips_without_fingerprint(tmp_path: Path):
    cfg = ScannerCheckpointConfig("report.json", "json", None)
    d = tmp_path / "trivy"
    d.mkdir()
    (d / "report.json").write_text('{"Results":[]}', encoding="utf-8")
    cp = {"steps": {}}
    record_scanner_completed(cp, "trivy", cfg, d, "gh", "ch", target_fingerprint_ok=False)
    assert "scanner:trivy" not in cp.get("steps", {})


def test_load_checkpoint_file(tmp_path: Path):
    p = tmp_path / "logs" / "checkpoint.json"
    p.write_text(json.dumps({"version": 1, "steps": {}}), encoding="utf-8")
    data = load_checkpoint(p)
    assert data["version"] == 1
