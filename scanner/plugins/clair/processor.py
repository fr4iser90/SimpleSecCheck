#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_CLAIR_PARSE = ParseSpec(
    items_key="vulnerabilities",
    fields=(
        ("PkgName", "package"),
        ("Severity", "severity"),
        ("VulnerabilityID", "vulnerability"),
        ("Title", "title"),
        ("Description", "description"),
    ),
)

_CLAIR_HTML = ToolHtmlSpec(
    title="Clair Container Image Vulnerability Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>',
    columns=(
        ColumnSpec("Package", "PkgName"),
        ColumnSpec("Severity", lambda f: str(f.get("Severity", "")).upper()),
        ColumnSpec("CVE", "VulnerabilityID"),
        ColumnSpec("Title", "Title"),
    ),
    severity_getter=lambda f: str(f.get("Severity", "")).upper(),
)

_CLAIR_POLICY = ToolPolicySpec(
    rule_id_field="VulnerabilityID",
    path_field="PkgName",
    message_field="Title",
    rule_id_mode="regex",
    accept_tool="Clair",
    accept_line_getter=lambda f: "",
)

CLAIR_POLICY_EXAMPLE = '''  "clair": {
    "accepted_findings": [
      {
        "rule_id": "CVE-2019-.*",
        "path_regex": "openssl|libssl",
        "message_regex": "Low.*severity",
        "reason": "OpenSSL low severity, patched in next base"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Clair",
    parse_spec=_CLAIR_PARSE,
    html_spec=_CLAIR_HTML,
    policy_spec=_CLAIR_POLICY,
    policy_example_snippet=CLAIR_POLICY_EXAMPLE,
    policy_key="clair",
)
