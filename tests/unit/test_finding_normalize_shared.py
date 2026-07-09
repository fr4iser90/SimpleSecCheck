"""Tests for shared finding field normalization (used by backend API)."""
from shared.finding_normalize import normalize_finding_fields


def test_normalize_finding_fields_semgrep_shape():
    fields = normalize_finding_fields(
        {
            "tool": "Semgrep",
            "severity": "HIGH",
            "path": "src/auth.py",
            "line": 42,
            "message": "SQL injection risk",
            "rule_id": "python.sql.injection",
        }
    )
    assert fields["severity"] == "HIGH"
    assert fields["path"] == "src/auth.py"
    assert fields["line"] == "42"
    assert fields["rule_id"] == "python.sql.injection"


def test_normalize_finding_fields_alternate_keys():
    fields = normalize_finding_fields(
        {
            "check_id": "B101",
            "file": "app.py",
            "line_number": 7,
            "issue_text": "Use of assert",
            "level": "medium",
        }
    )
    assert fields["severity"] == "MEDIUM"
    assert fields["rule_id"] == "B101"
    assert fields["path"] == "app.py"
    assert fields["message"] == "Use of assert"
