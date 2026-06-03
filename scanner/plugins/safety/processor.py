#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_SAFETY_PARSE = ParseSpec(
    items_key="vulnerabilities",
    fields=(
        ("package", "package"),
        ("version", "installed_version"),
        ("vulnerability_id", "vulnerability_id"),
        ("severity", "severity"),
        ("description", "description"),
        ("cve", "cve"),
        ("advisory", "advisory"),
        ("specs", "specs"),
        ("more_info_url", "more_info_url"),
    ),
)

_SAFETY_HTML = ToolHtmlSpec(
    title="Safety Python Dependency Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Python dependency vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Package", "package"),
        ColumnSpec("Version", "version"),
        ColumnSpec("Vulnerability ID", "vulnerability_id"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Description", "description"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_SAFETY_POLICY = ToolPolicySpec(
    rule_id_field="vulnerability_id",
    path_field="package",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Safety",
    accept_line_getter=lambda f: "",
)

SAFETY_POLICY_EXAMPLE = '''  "safety": {
    "accepted_findings": [
      {
        "rule_id": "12345",
        "path_regex": "dev-dependency|optional",
        "message_regex": "development only",
        "reason": "Vulnerable package scoped to dev/tooling, not shipped app code"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Safety",
    parse_spec=_SAFETY_PARSE,
    html_spec=_SAFETY_HTML,
    policy_spec=_SAFETY_POLICY,
    policy_example_snippet=SAFETY_POLICY_EXAMPLE,
    policy_key="safety",
)
