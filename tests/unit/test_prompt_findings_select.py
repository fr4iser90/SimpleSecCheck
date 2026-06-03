#!/usr/bin/env python3
import pytest

from application.helpers.prompt_findings_select import select_findings_for_prompt


def _f(tool, severity, path="a.py"):
    return {"tool": tool, "severity": severity, "path": path, "line": "1", "message": "m", "rule_id": "r"}


def test_select_prefers_high_before_low():
    findings = [_f("Bandit", "LOW", "z.py"), _f("Semgrep", "HIGH", "a.py"), _f("Semgrep", "HIGH", "b.py")]
    selected, meta = select_findings_for_prompt(findings, max_findings=2, min_severity="HIGH")
    assert len(selected) == 2
    assert all(s["severity"] == "HIGH" for s in selected)
    assert meta["included"] == 2


def test_select_tool_filter():
    findings = [_f("Bandit", "HIGH"), _f("Semgrep", "HIGH")]
    selected, meta = select_findings_for_prompt(findings, max_findings=10, min_severity="ALL", tool="Semgrep")
    assert len(selected) == 1
    assert selected[0]["tool"] == "Semgrep"
    assert meta["matched"] == 1
