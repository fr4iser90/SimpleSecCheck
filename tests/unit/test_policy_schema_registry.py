"""Policy schema registry — sync with plugin processors."""
import pytest

from scanner.core.policy_schema_registry import (
    POLICY_KEY_ALIASES,
    build_tool_blocks,
    discover_policy_tools,
    display_name_to_policy_key,
    resolve_policy_key,
)
from scanner.core.finding_policy_validate import validate_policy_data
from scanner.core.policy_engine import ToolPolicySpec


def test_discover_includes_npm_audit_and_owasp_dc():
    tools = discover_policy_tools()
    assert "npm_audit" in tools
    assert "owasp_dc" in tools


def test_npm_audit_matchers_use_dependency_path_and_severity():
    block = build_tool_blocks(tools_filter={"npm_audit"})["npm_audit"]
    matchers = block["matchers"]
    assert matchers["path_regex"]["finding_field"] == "dependency_path"
    assert matchers["message_regex"]["finding_field"] == "severity"


def test_owasp_alias_resolves():
    canonical, hint = resolve_policy_key("owasp_dependency_check")
    assert canonical == "owasp_dc"
    assert hint


def test_display_name_maps_npm_audit():
    m = display_name_to_policy_key()
    assert m.get("npm audit") == "npm_audit"


def test_validate_rejects_unknown_tool_key():
    result = validate_policy_data(
        {
            "not_a_real_scanner": {
                "accepted_findings": [{"reason": "x"}],
            }
        }
    )
    assert not result["valid"]
    assert any("Unknown" in e for e in result["errors"])


def test_validate_accepts_npm_audit_rule_with_dry_run():
    spec = discover_policy_tools()["npm_audit"].policy_spec
    finding = {
        "package": "esbuild",
        "severity": "moderate",
        "dependency_path": "vite > esbuild",
    }
    policy = {
        "npm_audit": {
            "accepted_findings": [
                {
                    "rule_id": "esbuild",
                    "path_regex": ".*",
                    "message_regex": "moderate",
                    "reason": "dev-only",
                }
            ]
        }
    }
    result = validate_policy_data(
        policy,
        sample_findings={"npm_audit": [finding]},
    )
    assert result["valid"], result["errors"]
    assert result["dry_run"]["npm_audit"]["findings_would_accept"] == 1


def test_all_discovered_tools_have_matchers():
    for pk, meta in discover_policy_tools().items():
        block = build_tool_blocks(tools_filter={pk})[pk]
        assert block["policy_key"] == pk
        assert block["matchers"]
        assert meta.policy_spec.policy_rule_id_key in block["matchers"]
