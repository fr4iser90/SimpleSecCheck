"""Unit tests for finding policy schema API and domain module."""
import pytest

from domain.policies.finding_policy_schema import (
    get_finding_policy_schema,
    parse_tools_query,
    policy_keys_from_findings,
)

try:
    from scanner.core.policy_schema_registry import discover_policy_tools
except ImportError:
    discover_policy_tools = None


def test_schema_version_is_2():
    schema = get_finding_policy_schema()
    assert schema["schema_version"] == "2"
    assert "policy_key_aliases" in schema


@pytest.mark.skipif(discover_policy_tools is None, reason="scanner not on path")
def test_tool_blocks_match_all_processors_with_policy():
    expected = set(discover_policy_tools().keys())
    schema = get_finding_policy_schema()
    assert expected.issubset(set(schema["tools"].keys()))


def test_npm_audit_has_matchers():
    schema = get_finding_policy_schema(tools_filter={"npm_audit"})
    npm = schema["tools"]["npm_audit"]
    assert npm["matchers"]["path_regex"]["finding_field"] == "dependency_path"
    assert "npm audit" in npm["display_names"]


def test_gitleaks_uses_file_and_description_regex():
    schema = get_finding_policy_schema(tools_filter={"gitleaks"})
    fields = schema["tools"]["gitleaks"]["accepted_findings"]["items"]["fields"]
    assert "file_regex" in fields
    assert "description_regex" in fields
    assert "path_regex" not in fields


def test_semgrep_block_has_dedupe_and_severity_overrides():
    schema = get_finding_policy_schema(tools_filter={"semgrep"})
    semgrep = schema["tools"]["semgrep"]
    assert "accepted_findings" in semgrep
    assert "severity_overrides" in semgrep
    assert "dedupe" in semgrep


def test_parse_tools_query():
    assert parse_tools_query(None) is None
    assert parse_tools_query("") is None
    assert parse_tools_query("semgrep, gitleaks") == {"semgrep", "gitleaks"}


def test_get_finding_policy_schema_filters_tools():
    full = get_finding_policy_schema()
    filtered = get_finding_policy_schema(tools_filter={"semgrep"})
    assert len(full["tools"]) > 1
    assert list(filtered["tools"].keys()) == ["semgrep"]
    assert "dedupe" in filtered["tools"]["semgrep"]


def test_policy_keys_from_findings_uses_policy_key_field():
    keys = policy_keys_from_findings(
        [{"tool": "npm audit", "policy_key": "npm_audit"}]
    )
    assert keys == {"npm_audit"}


def test_policy_keys_from_findings_maps_display_name():
    keys = policy_keys_from_findings([{"tool": "OWASP DC"}])
    assert "owasp_dc" in keys


def test_schema_documents_inline_separately():
    schema = get_finding_policy_schema()
    assert "inline_suppression_syntax" in schema
    assert "inline_suppressions" not in schema["tools"]


@pytest.fixture
def client():
    pytest.importorskip("pydantic_settings")
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)


def test_finding_policy_schema_endpoint_requires_auth(client):
    response = client.get("/api/v1/finding-policy/schema")
    assert response.status_code == 401


def test_finding_policy_schema_endpoint_with_guest_session(client):
    guest = client.post("/api/v1/auth/guest")
    assert guest.status_code == 200
    token = guest.json().get("access_token")
    assert token

    response = client.get(
        "/api/v1/finding-policy/schema",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "2"
    assert data["default_path"] == ".scanning/finding-policy.json"
    assert "semgrep" in data["tools"]
    assert "matchers" in data["tools"]["npm_audit"]
    assert data["minimal_example"]["semgrep"]["accepted_findings"][0]["reason"]


def test_finding_policy_schema_tools_query_param(client):
    guest = client.post("/api/v1/auth/guest")
    token = guest.json()["access_token"]
    response = client.get(
        "/api/v1/finding-policy/schema?tools=gitleaks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert list(response.json()["tools"].keys()) == ["gitleaks"]


def test_finding_policy_validate_endpoint(client):
    guest = client.post("/api/v1/auth/guest")
    token = guest.json()["access_token"]
    response = client.post(
        "/api/v1/finding-policy/validate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "policy": {
                "owasp_dependency_check": {
                    "accepted_findings": [{"rule_id": "GHSA-x", "reason": "ok"}],
                }
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert any("deprecated" in w.lower() or "owasp" in w.lower() for w in data["warnings"])
