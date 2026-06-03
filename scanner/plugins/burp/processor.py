#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_BURP_PARSE = ParseSpec(
    items_key="vulnerabilities",
    fields=(
        ("name", "name"),
        ("description", "description"),
        ("severity", "severity"),
        ("host", "host"),
        ("path", "path"),
        ("remediation", "remediation"),
    ),
)

_BURP_HTML = ToolHtmlSpec(
    title="Burp Suite Web Application Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web application vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Finding", "name"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Host", "host"),
        ColumnSpec("Path", "path"),
        ColumnSpec("Description", "description"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_BURP_POLICY = ToolPolicySpec(
    rule_id_field="name",
    path_getter=lambda f: f.get("path", "") or f.get("host", ""),
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Burp Suite",
    accept_path_getter=lambda f: f.get("path", "") or f.get("host", ""),
    accept_line_getter=lambda f: "",
)

BURP_POLICY_EXAMPLE = '''  "burp_suite": {
    "accepted_findings": [
      {
        "rule_id": "Information disclosure",
        "path_regex": "/debug|/version",
        "message_regex": "version.*disclosure",
        "reason": "Version endpoint is internal-only, not exposed"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Burp Suite",
    parse_spec=_BURP_PARSE,
    html_spec=_BURP_HTML,
    policy_spec=_BURP_POLICY,
    policy_example_snippet=BURP_POLICY_EXAMPLE,
    policy_key="burp_suite",
)
