"""Unit tests for scanner.core.inline_suppressions."""
from __future__ import annotations

from pathlib import Path

import pytest

from scanner.core.inline_suppressions import (
    apply_inline_suppressions,
    build_suppression_index,
    get_inline_config,
    is_finding_inline_suppressed,
    normalize_finding_path,
    parse_line_suppressions,
)


def test_parse_nosec_all_and_reason():
    sup = parse_line_suppressions(
        "cur.execute(sql, args)  # nosec B608 — parameterized query via %s"
    )
    assert sup is not None
    assert "B608" in sup.nosec_ids
    assert "parameterized query via %s" in sup.reason


def test_parse_nosemgrep_rule_list():
    sup = parse_line_suppressions(
        "x = 1  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query"
    )
    assert sup is not None
    assert "python.sqlalchemy.security.sqlalchemy-execute-raw-query" in sup.nosemgrep_ids


def test_parse_eslint_disable_next_line():
    sup = parse_line_suppressions("// eslint-disable-next-line no-eval, security/detect-eval-with-expression")
    assert sup is not None
    assert sup.eslint_disable_next_all is False
    assert "no-eval" in sup.eslint_disable_next


def test_parse_ssc_accept():
    sup = parse_line_suppressions("# ssc:accept py/sql-injection — values bound via %s")
    assert sup is not None
    assert "py/sql-injection" in sup.ssc_accept_ids
    assert "values bound via %s" in sup.reason


def test_get_inline_config_defaults():
    cfg = get_inline_config()
    assert cfg["enabled"] is True
    assert cfg["line_lookback"] == 1


def test_get_inline_config_from_env(monkeypatch):
    monkeypatch.setenv("SSC_INLINE_SUPPRESSIONS_ENABLED", "false")
    monkeypatch.setenv("SSC_INLINE_SUPPRESSIONS_LINE_LOOKBACK", "2")
    cfg = get_inline_config()
    assert cfg["enabled"] is False
    assert cfg["line_lookback"] == 2


def test_normalize_finding_path_strips_target_prefix():
    rel = normalize_finding_path("/app/target/apps/foo.py", "/app/target")
    assert rel == "apps/foo.py"


def test_build_suppression_index(tmp_path: Path):
    src = tmp_path / "apps" / "db.py"
    src.parent.mkdir(parents=True)
    src.write_text(
        "def update():\n"
        "    cur.execute(sql, args)  # nosec B608  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query\n",
        encoding="utf-8",
    )
    index = build_suppression_index(str(tmp_path))
    assert ("apps/db.py", 2) in index


def test_codeql_suppressed_by_nosemgrep_on_same_line(tmp_path: Path):
    src = tmp_path / "dash.py"
    src.write_text(
        "cur.execute(f\"UPDATE t SET {cols}\", args)  # nosemgrep: py/sql-injection\n",
        encoding="utf-8",
    )
    index = build_suppression_index(str(tmp_path))
    finding = {
        "path": str(src),
        "start": 1,
        "rule_id": "py/sql-injection",
        "message": "SQL injection",
    }
    suppressed, reason, tag = is_finding_inline_suppressed(
        finding,
        "codeql",
        index,
        str(tmp_path),
        get_inline_config(),
    )
    assert suppressed is True
    assert tag == "nosemgrep"


def test_bandit_b608_requires_matching_id(tmp_path: Path):
    src = tmp_path / "a.py"
    src.write_text("x = eval('1')  # nosec B101\n", encoding="utf-8")
    index = build_suppression_index(str(tmp_path))
    finding = {"filename": "a.py", "line_number": 1, "test_id": "B608", "rule_id": "B608"}
    suppressed, _, _ = is_finding_inline_suppressed(
        finding, "bandit", index, str(tmp_path), get_inline_config()
    )
    assert suppressed is False

    finding_b101 = {"filename": "a.py", "line_number": 1, "rule_id": "B101"}
    suppressed2, _, tag = is_finding_inline_suppressed(
        finding_b101, "bandit", index, str(tmp_path), get_inline_config()
    )
    assert suppressed2 is True
    assert tag == "nosec"


def test_eslint_disable_next_applies_to_following_line(tmp_path: Path):
    src = tmp_path / "app.js"
    src.write_text(
        "// eslint-disable-next-line no-console\nconsole.log('debug');\n",
        encoding="utf-8",
    )
    index = build_suppression_index(str(tmp_path))
    finding = {"path": "app.js", "line": 2, "rule_id": "no-console"}
    suppressed, _, tag = is_finding_inline_suppressed(
        finding, "eslint", index, str(tmp_path), get_inline_config()
    )
    assert suppressed is True
    assert tag == "eslint-disable-next-line"


def test_apply_inline_suppressions_filters_list(tmp_path: Path):
    src = tmp_path / "x.py"
    src.write_text("bad()  # nosec\nok()\n", encoding="utf-8")
    index = build_suppression_index(str(tmp_path))
    findings = [
        {"filename": "x.py", "line_number": 1, "rule_id": "B999", "message": "issue"},
        {"filename": "x.py", "line_number": 2, "rule_id": "B001", "message": "other"},
    ]
    remaining, accepted = apply_inline_suppressions(
        findings,
        index,
        tool_key="bandit",
        tool_name="Bandit",
        target_root=str(tmp_path),
    )
    assert len(remaining) == 1
    assert len(accepted) == 1
    assert accepted[0]["accept_source"] == "inline"
    assert accepted[0]["suppress_tag"] == "nosec"


def test_multiline_nosemgrep_suppresses_next_line(tmp_path: Path):
    src = tmp_path / "db.py"
    src.write_text(
        "def run():\n"
        "    cur.execute(  # nosemgrep: py/sql-injection\n"
        '        f"UPDATE t SET {col}", args)\n',
        encoding="utf-8",
    )
    index = build_suppression_index(str(tmp_path))
    finding = {"path": "db.py", "start": 3, "rule_id": "py/sql-injection", "message": "sqli"}
    suppressed, _, tag = is_finding_inline_suppressed(
        finding, "codeql", index, str(tmp_path), get_inline_config()
    )
    assert suppressed is True
    assert tag == "nosemgrep"


def test_inline_disabled_skips_filtering(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SSC_INLINE_SUPPRESSIONS_ENABLED", "false")
    src = tmp_path / "x.py"
    src.write_text("bad()  # nosec\n", encoding="utf-8")
    index = build_suppression_index(str(tmp_path))
    findings = [{"filename": "x.py", "line_number": 1, "rule_id": "B999"}]
    remaining, accepted = apply_inline_suppressions(
        findings,
        index,
        tool_key="bandit",
        tool_name="Bandit",
        target_root=str(tmp_path),
        config=get_inline_config(),
    )
    assert len(remaining) == 1
    assert accepted == []
