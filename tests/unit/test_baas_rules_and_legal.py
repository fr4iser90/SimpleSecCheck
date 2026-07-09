"""Unit tests for BaaS rules scanner and legal content service."""
import json
import tempfile
from pathlib import Path

import pytest

from scanner.plugins.baas_rules.scanner import BaasRulesScanner
from domain.services.legal_content_service import (
    build_public_legal_response,
    normalize_legal_config,
    render_impressum_de,
    render_impressum_en,
    render_privacy_en,
    render_terms_de,
    render_terms_en,
    validate_legal_config,
)


@pytest.fixture
def tmp_scan(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    return BaasRulesScanner(str(tmp_path), str(results), str(tmp_path / "scan.log"))


def test_firebase_open_allow_detected(tmp_scan, tmp_path):
    rules = tmp_path / "firestore.rules"
    rules.write_text(
        'rules_version = "2";\n'
        "service cloud.firestore {\n"
        "  match /databases/{database}/documents {\n"
        "    match /{document=**} {\n"
        "      allow read, write: if true;\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    issues = tmp_scan.analyze_file(rules)
    assert any(i["rule_id"] == "firebase_open_allow" for i in issues)
    assert any(i["severity"] == "CRITICAL" for i in issues)


def test_supabase_open_rls_detected(tmp_scan, tmp_path):
    mig_dir = tmp_path / "supabase" / "migrations"
    mig_dir.mkdir(parents=True)
    sql = mig_dir / "20240101000000_init.sql"
    sql.write_text(
        "CREATE TABLE profiles (id uuid primary key);\n"
        "CREATE POLICY public_read ON profiles FOR SELECT USING (true);\n",
        encoding="utf-8",
    )
    issues = tmp_scan.analyze_file(sql)
    assert any(i["rule_id"] == "supabase_rls_open_using" for i in issues)


def test_scan_writes_report(tmp_scan, tmp_path):
    (tmp_path / "storage.rules").write_text(
        "rules_version = '2';\n"
        "service firebase.storage {\n"
        "  match /b/{bucket}/o {\n"
        "    match /{allPaths=**} { allow read: if true; }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    assert tmp_scan.scan() is True
    report = json.loads((tmp_path / "results" / "report.json").read_text())
    assert report["total_issues"] >= 1


def test_legal_impressum_de():
    cfg = normalize_legal_config({
        "enabled": True,
        "company_name": "Test GmbH",
        "address": "Musterstraße 1\n12345 Berlin",
        "email": "info@test.de",
    })
    text = render_impressum_de(cfg)
    assert "Test GmbH" in text
    assert "§ 5 TMG" in text


def test_legal_validation_warnings():
    cfg = normalize_legal_config({"enabled": True, "locale": "de"})
    warnings = validate_legal_config(cfg)
    assert "missing_company_name" in warnings
    assert "missing_address" in warnings
    assert "missing_email" in warnings


def test_english_legal_templates():
    cfg = normalize_legal_config({
        "enabled": True,
        "locale": "en",
        "company_name": "Acme GmbH",
        "address": "1 Main St",
        "email": "legal@acme.test",
        "terms_enabled": True,
    })
    pages = build_public_legal_response(cfg, state_config={"use_case": "public_web"})["pages"]
    assert "Legal Notice" in pages["impressum"]["content"]
    assert "Privacy Policy" in pages["privacy"]["content"]
    assert "Terms of Service" in pages["terms"]["content"]
    assert "GDPR" in pages["privacy"]["content"]
    assert render_terms_en(cfg).startswith("## Terms of Service")


def test_public_legal_disabled_by_default():
    pub = build_public_legal_response(normalize_legal_config(None))
    assert pub["enabled"] is False
    assert pub["footer_links"] == []


def test_terms_auto_enabled_for_accounts():
    cfg = normalize_legal_config(
        {"enabled": True, "company_name": "X", "address": "Y", "email": "a@b.de"},
        {"use_case": "public_web"},
    )
    assert cfg["terms_enabled"] is True
    pub = build_public_legal_response(cfg, state_config={"use_case": "public_web"})
    assert pub["require_terms_acceptance"] is True
    assert "terms" in pub["pages"]
    assert "Nutzungsbedingungen" in pub["pages"]["terms"]["content"]


def test_terms_template_covers_accounts():
    text = render_terms_de({"company_name": "Test GmbH", "email": "legal@test.de"})
    assert "Registrierung" in text
    assert "Account" in text
