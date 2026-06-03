#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_SNYK_PARSE = ParseSpec(
    items_key="vulnerabilities",
    skipped_key="skipped",
    fields=(
        ("package", "package"),
        ("version", "version"),
        ("vulnerability_id", "id"),
        ("severity", "severity"),
        ("title", "title"),
        ("description", "description"),
        ("cve", "cve"),
        ("cwe", "cwe"),
        ("cvss_score", "cvssScore"),
    ),
)

_SNYK_HTML = ToolHtmlSpec(
    title="Snyk Vulnerability Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found by Snyk.</div>',
    skipped_html=(
        '<div class="all-clear"><span class="icon sev-PASSED">⏭️</span> '
        "Snyk scan was skipped. Set SNYK_TOKEN environment variable to enable Snyk vulnerability scanning.</div>"
    ),
    columns=(
        ColumnSpec("Package", "package"),
        ColumnSpec("Version", "version"),
        ColumnSpec("Vulnerability ID", "vulnerability_id"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "MEDIUM")).upper()),
        ColumnSpec("Title", "title"),
        ColumnSpec("CVSS Score", "cvss_score"),
    ),
    severity_getter=lambda f: str(f.get("severity", "MEDIUM")).upper(),
)

_SNYK_POLICY = ToolPolicySpec(
    rule_id_field="vulnerability_id",
    path_field="package",
    message_field="title",
    rule_id_mode="regex",
    accept_tool="Snyk",
    accept_line_getter=lambda f: "",
)

SNYK_POLICY_EXAMPLE = '''  "snyk": {
    "accepted_findings": [
      {
        "rule_id": "SNYK-JS-LODASH-.*",
        "path_regex": "lodash",
        "message_regex": "Prototype Pollution",
        "reason": "Lodash pinned and used in safe context only"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Snyk",
    parse_spec=_SNYK_PARSE,
    html_spec=_SNYK_HTML,
    policy_spec=_SNYK_POLICY,
    policy_example_snippet=SNYK_POLICY_EXAMPLE,
    policy_key="snyk",
)
