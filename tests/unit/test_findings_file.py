"""Unit tests for findings.json loader."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def findings_module(monkeypatch, tmp_path):
    """Load findings_file with a mocked settings module (no pydantic_settings)."""
    mock_settings = type(sys)("config.settings")
    mock_settings.get_settings = lambda: type(
        "S", (), {"RESULTS_DIR_HOST": str(tmp_path)}
    )()
    monkeypatch.setitem(sys.modules, "config.settings", mock_settings)
    spec = importlib.util.spec_from_file_location(
        "findings_file",
        _BACKEND / "application" / "helpers" / "findings_file.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_findings_json_path_structure(findings_module):
    p = findings_module.findings_json_path("scan-abc-123")
    assert p.name == "findings.json"
    assert "scan-abc-123" in str(p)
    assert p.parent.name == "summary"


def test_load_findings_payload_from_file(tmp_path, findings_module):
    scan_id = "test-scan-id"
    summary_dir = tmp_path / scan_id / "summary"
    summary_dir.mkdir(parents=True)
    doc = {
        "generated_at": "2026-05-17T12:00:00Z",
        "findings": [
            {
                "tool": "semgrep",
                "severity": "HIGH",
                "path": "app.py",
                "line": "10",
                "message": "issue",
                "rule_id": "rule-1",
            }
        ],
        "summary": {"total_vulnerabilities": 1, "critical_vulnerabilities": 0},
    }
    (summary_dir / "findings.json").write_text(json.dumps(doc), encoding="utf-8")

    payload, source = findings_module.load_findings_payload(scan_id)
    assert source == "file"
    assert payload is not None
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["rule_id"] == "rule-1"


def test_load_findings_payload_missing(findings_module):
    payload, source = findings_module.load_findings_payload("no-such-scan")
    assert payload is None
    assert source == "missing"
