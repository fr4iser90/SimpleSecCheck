#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_ESLINT_PARSE = ParseSpec(
    root_is_list=True,
    nested_items_key="messages",
    parent_fields=(("file_path", "filePath"),),
    fields=(
        ("rule_id", "ruleId"),
        ("severity", "severity"),
        ("message", "message"),
        ("line", "line"),
        ("column", "column"),
        ("end_line", "endLine"),
        ("end_column", "endColumn"),
    ),
    skip_if=lambda f: f.get("severity") == 0,
)

_ESLINT_HTML = ToolHtmlSpec(
    title="ESLint Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No ESLint security issues found.</div>',
    columns=(
        ColumnSpec("File", "file_path"),
        ColumnSpec("Rule", "rule_id"),
        ColumnSpec(
            "Severity",
            lambda f: "ERROR"
            if int(f.get("severity", 2) or 2) == 2
            else ("WARNING" if int(f.get("severity", 2) or 2) == 1 else "INFO"),
        ),
        ColumnSpec("Message", "message"),
        ColumnSpec("Line", "line"),
    ),
    severity_getter=lambda f: "ERROR"
    if int(f.get("severity", 2) or 2) == 2
    else ("WARNING" if int(f.get("severity", 2) or 2) == 1 else "INFO"),
)

_ESLINT_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="file_path",
    message_field="message",
    rule_id_mode="regex",
    accept_tool="ESLint",
)

ESLINT_POLICY_EXAMPLE = '''  "eslint": {
    "accepted_findings": [
      {
        "rule_id": "no-console",
        "path_regex": "scripts/|tools/.*\\.js$",
        "message_regex": "console",
        "reason": "Console allowed in build/script files"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="ESLint",
    parse_spec=_ESLINT_PARSE,
    html_spec=_ESLINT_HTML,
    policy_spec=_ESLINT_POLICY,
    policy_example_snippet=ESLINT_POLICY_EXAMPLE,
    policy_key="eslint",
)
