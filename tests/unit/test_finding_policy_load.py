#!/usr/bin/env python3
import json

import pytest

from scanner.core.finding_policy import load_policy
from scanner.core.policy_engine import ToolPolicySpec, apply_policy_with_severity_overrides
from scanner.core.policy_matching import normalize_finding_paths


def test_load_policy_ignores_metadata_keys(tmp_path):
    policy_file = tmp_path / "finding-policy.json"
    policy_file.write_text(
        json.dumps(
            {
                "version": "1",
                "bandit": {
                    "accepted_findings": [
                        {
                            "rule_id": "B110",
                            "path_regex": "apps/backend/.*\\.py$",
                            "reason": "ok",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    loaded = load_policy(str(policy_file))
    assert "version" not in loaded
    assert "bandit" in loaded


def test_apply_policy_strips_target_prefix_and_accepts():
    spec = ToolPolicySpec(
        rule_id_field="rule_id",
        path_field="path",
        message_field="message",
        accept_tool="Semgrep",
    )
    findings = [
        {
            "rule_id": "test.rule",
            "path": "/target/apps/backend/x.py",
            "message": "issue",
            "severity": "HIGH",
            "start": 10,
        }
    ]
    tool_policy = {
        "accepted_findings": [
            {
                "rule_id": "test.rule",
                "path_regex": "apps/backend/.*\\.py$",
                "reason": "accepted",
            }
        ]
    }
    processed, accepted = apply_policy_with_severity_overrides(
        findings=findings,
        tool_policy=tool_policy,
        spec=spec,
    )
    assert processed == []
    assert len(accepted) == 1
    assert accepted[0]["path"] == "apps/backend/x.py"


def test_normalize_finding_paths():
    f = normalize_finding_paths({"path": "/target/foo.py", "filename": "/app/target/bar.py"})
    assert f["path"] == "foo.py"
    assert f["filename"] == "bar.py"


def test_semgrep_dedupe_max_per_rule():
    spec = ToolPolicySpec(
        rule_id_field="rule_id",
        path_field="path",
        message_field="message",
        accept_line_getter=lambda f: f.get("start", ""),
        accept_tool="Semgrep",
    )
    findings = [
        {"rule_id": "r1", "path": "/target/a.py", "message": "m", "severity": "LOW", "start": i}
        for i in range(1, 8)
    ]
    tool_policy = {
        "dedupe": {
            "enabled": True,
            "line_window": 0,
            "line_field": "start",
            "max_deduped_per_rule": 2,
            "group_fields": ["rule_id", "path", "message", "severity"],
        }
    }
    processed, _ = apply_policy_with_severity_overrides(
        findings=findings,
        tool_policy=tool_policy,
        spec=spec,
    )
    assert len(processed) <= 2
