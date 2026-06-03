#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_BANDIT_PARSE = ParseSpec(
    items_key="results",
    fields=(
        ("rule_id", "test_id"),
        ("test_name", "test_name"),
        ("severity", "issue_severity"),
        ("confidence", "issue_confidence"),
        ("filename", "filename"),
        ("line_number", "line_number"),
        ("code", "code"),
        ("message", "issue_text"),
    ),
)

_BANDIT_HTML = ToolHtmlSpec(
    title="Bandit Python Security Scan",
    empty_html="<p>No Python security vulnerabilities found.</p>",
    columns=(
        ColumnSpec("Test ID", "rule_id"),
        ColumnSpec("Severity", "severity"),
        ColumnSpec("Confidence", "confidence"),
        ColumnSpec("File", "filename"),
        ColumnSpec("Line", "line_number"),
        ColumnSpec("Issue", "message"),
        ColumnSpec("Code", "code"),
    ),
    severity_getter="severity",
)

_BANDIT_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="filename",
    message_field="message",
    rule_id_mode="exact",
    accept_tool="Bandit",
)

BANDIT_POLICY_EXAMPLE = '''  "bandit": {
    "accepted_findings": [
      {
        "rule_id": "B101",
        "path_regex": "tests/.*|conftest\\.py$",
        "message_regex": "assert_used",
        "reason": "Assert used only in tests, acceptable"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Bandit",
    parse_spec=_BANDIT_PARSE,
    html_spec=_BANDIT_HTML,
    policy_spec=_BANDIT_POLICY,
    policy_example_snippet=BANDIT_POLICY_EXAMPLE,
    policy_key="bandit",
)
