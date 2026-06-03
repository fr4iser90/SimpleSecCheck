#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_OWASP_PARSE = ParseSpec(
    items_key="dependencies",
    nested_items_key="vulnerabilities",
    parent_fields=(
        (
            "Dependency",
            lambda item, parent: f"{parent.get('fileName', 'Unknown')} ({parent.get('version', 'Unknown')})",
        ),
    ),
    fields=(
        ("Severity", "severity"),
        ("CVE", "name"),
        ("Title", "title"),
        ("Description", "description"),
        ("CVSS", "cvssScore"),
        ("CVSS_Vector", "cvssVector"),
        ("References", "references"),
    ),
)

_OWASP_HTML = ToolHtmlSpec(
    title="OWASP Dependency Check - Dependency Vulnerabilities",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No dependency vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Dependency", "Dependency"),
        ColumnSpec("Severity", lambda f: str(f.get("Severity", "")).upper()),
        ColumnSpec("CVE", "CVE"),
        ColumnSpec("CVSS Score", "CVSS"),
        ColumnSpec("Title", "Title"),
    ),
    severity_getter=lambda f: str(f.get("Severity", "")).upper(),
)

_OWASP_POLICY = ToolPolicySpec(
    rule_id_field="CVE",
    path_field="Dependency",
    message_getter=lambda f: f.get("Title", "") or f.get("Description", ""),
    rule_id_mode="regex",
    accept_tool="OWASP DC",
    accept_line_getter=lambda f: "",
)

OWASP_POLICY_EXAMPLE = '''  "owasp_dc": {
    "accepted_findings": [
      {
        "rule_id": "CVE-2021-44228",
        "path_regex": "log4j.*2\\.(1[0-4]|0\\.)",
        "message_regex": "Log4j.*RCE",
        "reason": "log4j in test scope only, not packaged"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="OWASP DC",
    parse_spec=_OWASP_PARSE,
    html_spec=_OWASP_HTML,
    policy_spec=_OWASP_POLICY,
    policy_example_snippet=OWASP_POLICY_EXAMPLE,
    policy_key="owasp_dc",
    ai_tool_name="OWASP DC",
)
