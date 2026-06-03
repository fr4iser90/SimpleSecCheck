#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_SONARQUBE_PARSE = ParseSpec(
    items_key="issues",
    fields=(
        ("severity", "severity"),
        ("component", "component"),
        ("message", "message"),
        ("line", "line"),
        ("rule", "rule"),
        ("type", "type"),
    ),
)

_SONARQUBE_HTML = ToolHtmlSpec(
    title="SonarQube Code Quality & Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code quality issues found.</div>',
    columns=(
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Component", "component"),
        ColumnSpec("Line", "line"),
        ColumnSpec("Message", "message"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_SONARQUBE_POLICY = ToolPolicySpec(
    rule_id_field="rule",
    path_field="component",
    message_field="message",
    rule_id_mode="regex",
    accept_tool="SonarQube",
    accept_line_getter=lambda f: f.get("line", ""),
)

SONARQUBE_POLICY_EXAMPLE = '''  "sonarqube": {
    "accepted_findings": [
      {
        "rule_id": "javascript:S1848",
        "path_regex": ".*\\.test\\.[jt]s$",
        "message_regex": "console\\.",
        "reason": "Console in test files only"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="SonarQube",
    parse_spec=_SONARQUBE_PARSE,
    html_spec=_SONARQUBE_HTML,
    policy_spec=_SONARQUBE_POLICY,
    policy_example_snippet=SONARQUBE_POLICY_EXAMPLE,
    policy_key="sonarqube",
)
