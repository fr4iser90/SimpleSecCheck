#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec, trivy_path, trivy_title
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_TRIVY_PARSE = ParseSpec(
    items_key="Results",
    nested_items_key="Vulnerabilities",
    fields=(
        ("PkgName", "PkgName"),
        ("Severity", "Severity"),
        ("VulnerabilityID", "VulnerabilityID"),
        ("Title", trivy_title),
        ("Description", "Description"),
        ("path", trivy_path),
        ("file", "PkgName"),
        ("message", trivy_title),
        ("rule_id", "VulnerabilityID"),
    ),
)

_TRIVY_HTML = ToolHtmlSpec(
    title="Trivy Dependency & Container Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in dependencies or containers.</div>',
    columns=(
        ColumnSpec("Package", "PkgName"),
        ColumnSpec("Severity", lambda f: str(f.get("Severity", "")).upper()),
        ColumnSpec("CVE", "VulnerabilityID"),
        ColumnSpec("Title", "Title"),
    ),
    severity_getter=lambda f: str(f.get("Severity", "")).upper(),
)

_TRIVY_POLICY = ToolPolicySpec(
    rule_id_field="VulnerabilityID",
    path_field="PkgName",
    message_field="Title",
    rule_id_mode="regex",
    accept_tool="Trivy",
    accept_line_getter=lambda f: "",
)

TRIVY_POLICY_EXAMPLE = '''  "trivy": {
    "accepted_findings": [
      {
        "rule_id": "CVE-2020-.*",
        "path_regex": "libxml2|libexpat",
        "message_regex": "Low severity.*unused",
        "reason": "Vendored lib with known low-severity CVE, mitigated"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Trivy",
    parse_spec=_TRIVY_PARSE,
    html_spec=_TRIVY_HTML,
    policy_spec=_TRIVY_POLICY,
    policy_example_snippet=TRIVY_POLICY_EXAMPLE,
    policy_key="trivy",
)
