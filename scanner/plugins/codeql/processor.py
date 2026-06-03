#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec, codeql_message, codeql_path, codeql_start
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_CODEQL_FIELDS = (
    ("rule_id", "ruleId"),
    ("level", "level"),
    ("message", codeql_message),
    ("path", codeql_path),
    ("start", codeql_start),
    ("severity", lambda item, parent: str(item.get("level", "note")).upper()),
)

_CODEQL_PARSE = ParseSpec(
    variants=(
        ParseSpec(items_key="runs", nested_items_key="results", fields=_CODEQL_FIELDS),
        ParseSpec(items_key="results", fields=_CODEQL_FIELDS),
        ParseSpec(root_is_list=True, fields=_CODEQL_FIELDS),
    ),
)

_CODEQL_HTML = ToolHtmlSpec(
    title="CodeQL Static Analysis",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No CodeQL findings detected.</div>',
    columns=(
        ColumnSpec("Rule", "rule_id"),
        ColumnSpec("File", "path"),
        ColumnSpec("Line", "start"),
        ColumnSpec("Message", "message"),
        ColumnSpec("Severity", "severity"),
    ),
    severity_getter="severity",
)

_CODEQL_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="path",
    message_field="message",
    rule_id_mode="regex",
    accept_tool="CodeQL",
    accept_line_getter=lambda f: f.get("start", ""),
)

CODEQL_POLICY_EXAMPLE = '''  "codeql": {
    "accepted_findings": [
      {
        "rule_id": "js/sql-injection",
        "path_regex": "tests/.*|fixtures/.*",
        "message_regex": "test.*query",
        "reason": "Test code using parameterized queries in shipped/runtime paths"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="CodeQL",
    parse_spec=_CODEQL_PARSE,
    html_spec=_CODEQL_HTML,
    policy_spec=_CODEQL_POLICY,
    policy_example_snippet=CODEQL_POLICY_EXAMPLE,
    policy_key="codeql",
)
