#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_BRAKEMAN_PARSE = ParseSpec(
    items_key="warnings",
    fields=(
        ("warning_type", "warning_type"),
        ("warning_code", "warning_code"),
        ("message", "message"),
        ("file", "file"),
        ("line", "line"),
        ("link", "link"),
        ("confidence", "confidence"),
        ("description", "description"),
    ),
)

_BRAKEMAN_HTML = ToolHtmlSpec(
    title="Brakeman Ruby on Rails Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Ruby security vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Type", "warning_type"),
        ColumnSpec("Confidence", "confidence"),
        ColumnSpec("File", "file"),
        ColumnSpec("Line", "line"),
        ColumnSpec("Message", "message"),
    ),
    severity_getter=lambda f: str(f.get("confidence", "")).upper(),
)

_BRAKEMAN_POLICY = ToolPolicySpec(
    rule_id_field="warning_type",
    path_field="file",
    message_field="message",
    rule_id_mode="regex",
    accept_tool="Brakeman",
    accept_line_getter=lambda f: f.get("line", ""),
)

BRAKEMAN_POLICY_EXAMPLE = '''  "brakeman": {
    "accepted_findings": [
      {
        "rule_id": "BasicAuth",
        "path_regex": "config/routes\\.rb",
        "message_regex": "basic.*auth",
        "reason": "Basic auth only for internal health check"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Brakeman",
    parse_spec=_BRAKEMAN_PARSE,
    html_spec=_BRAKEMAN_HTML,
    policy_spec=_BRAKEMAN_POLICY,
    policy_example_snippet=BRAKEMAN_POLICY_EXAMPLE,
    policy_key="brakeman",
)
