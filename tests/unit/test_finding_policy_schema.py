"""Unit tests for finding policy schema API and domain module."""
import pytest

from domain.policies.finding_policy_schema import (
    TOOL_BLOCKS,
    get_finding_policy_schema,
    parse_tools_query,
)


def test_tool_blocks_include_all_scanner_policy_keys():
    expected = {
        "semgrep",
        "gitleaks",
        "detect_secrets",
        "codeql",
        "bandit",
        "trivy",
        "npm_audit",
        "checkov",
        "burp_suite",
        "android_manifest",
        "ios_plist",
        "terraform_checkov",
        "owasp_dc",
    }
    assert expected.issubset(set(TOOL_BLOCKS.keys()))


def test_semgrep_block_has_dedupe_and_severity_overrides():
    semgrep = TOOL_BLOCKS["semgrep"]
    assert "accepted_findings" in semgrep
    assert "severity_overrides" in semgrep
    assert "dedupe" in semgrep


def test_gitleaks_uses_file_and_description_regex():
    fields = TOOL_BLOCKS["gitleaks"]["accepted_findings"]["items"]["fields"]
    assert "file_regex" in fields
    assert "description_regex" in fields
    assert "path_regex" not in fields


def test_detect_secrets_no_message_regex():
    fields = TOOL_BLOCKS["detect_secrets"]["accepted_findings"]["items"]["fields"]
    assert "path_regex" in fields
    assert "message_regex" not in fields


def test_codeql_rule_id_is_regex():
    fields = TOOL_BLOCKS["codeql"]["accepted_findings"]["items"]["fields"]
    assert "regex" in fields["rule_id"]["description"].lower()


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


def test_schema_notes_mention_root_dedupe_legacy():
    schema = get_finding_policy_schema()
    notes_text = " ".join(schema["notes"])
    assert "semgrep.dedupe" in notes_text
    assert "root" in notes_text.lower()


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
    assert data["schema_version"] == "1"
    assert data["default_path"] == ".scanning/finding-policy.json"
    assert "semgrep" in data["tools"]
    assert "gitleaks" in data["tools"]
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
