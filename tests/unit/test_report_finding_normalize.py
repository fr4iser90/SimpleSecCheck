#!/usr/bin/env python3
from scanner.output.ai_normalizer_utils import format_rule_message_cell, normalize_finding_fields


def test_npm_audit_fields():
    fields = normalize_finding_fields(
        {
            "package": "esbuild",
            "severity": "moderate",
            "dependency_path": "apps/frontend > esbuild",
            "via": ["GHSA-xxxx"],
            "range": "<0.24.0",
        }
    )
    assert fields["rule_id"] == "esbuild"
    assert "apps/frontend" in fields["path"]
    assert "GHSA" in fields["message"]


def test_owasp_fields():
    fields = normalize_finding_fields(
        {
            "Dependency": "package-lock.json (1.2.3)",
            "Severity": "MEDIUM",
            "CVE": "CVE-2024-1234",
            "Title": "esbuild dev server CORS",
            "Description": "Full advisory text",
        }
    )
    assert fields["rule_id"] == "CVE-2024-1234"
    assert "package-lock" in fields["path"]
    assert fields["message"] == "esbuild dev server CORS"


def test_format_rule_message_cell_no_lone_colon():
    assert format_rule_message_cell("", "advisory") == "advisory"
    assert format_rule_message_cell("CVE-1", "title") == "CVE-1: title"
    assert format_rule_message_cell("B101", "") == "B101"


def test_eslint_none_rule_id_stripped():
    fields = normalize_finding_fields(
        {"rule_id": "None", "message": "Unused eslint-disable", "line": 280}
    )
    assert fields["rule_id"] == ""
    assert format_rule_message_cell(fields["rule_id"], fields["message"]) == "Unused eslint-disable"
