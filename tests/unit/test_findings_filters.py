"""Unit tests for findings pagination filters (Sprint 1)."""
import sys
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parent.parent.parent / "backend"
if _BACKEND.exists() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from application.helpers.findings_pagination import (
    apply_findings_filters,
    build_findings_poll_path,
    filter_findings_by_rule_id,
    filter_findings_by_tool,
)


def _item(tool, path, rule_id, severity="HIGH"):
    return SimpleNamespace(
        tool=tool,
        policy_key=tool,
        severity=severity,
        path=path,
        line="1",
        message="msg",
        rule_id=rule_id,
    )


def test_filter_by_tool():
    items = [
        _item("semgrep", "a.py", "r1"),
        _item("bandit", "b.py", "r2"),
    ]
    out = filter_findings_by_tool(items, "semgrep")
    assert len(out) == 1
    assert out[0].tool == "semgrep"


def test_filter_by_path_prefix_and_rule_id_regex():
    items = [
        _item("semgrep", "src/auth.py", "python.lang.security.weak-hash"),
        _item("semgrep", "tests/auth.py", "python.lang.security.weak-hash"),
        _item("semgrep", "src/util.py", "other.rule"),
    ]
    out = apply_findings_filters(
        items,
        path_prefix="src/",
        rule_id=r"python\.lang\.security\.",
    )
    assert len(out) == 1
    assert out[0].path == "src/auth.py"


def test_rule_id_invalid_regex_falls_back_to_literal():
    items = [_item("semgrep", "x.py", "bad[rule")]
    out = filter_findings_by_rule_id(items, "bad[rule")
    assert len(out) == 1


def test_build_findings_poll_path_includes_filters():
    path = build_findings_poll_path(
        "scan-1",
        limit=50,
        offset=0,
        severity="CRITICAL,HIGH",
        tool="semgrep",
        path_prefix="src/",
        rule_id="python.*",
    )
    assert "tool=semgrep" in path
    assert "path_prefix=src%2F" in path or "path_prefix=src/" in path
    assert "rule_id=python" in path
