#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_WAPITI_PARSE = ParseSpec(
    items_key="vulnerabilities",
    dict_key_parent_field="category",
    inner_dict_key_parent_field="target",
    parent_fields=(
        ("category", "category"),
        ("target", "target"),
    ),
    fields=(
        ("description", lambda item, parent: item.get("desc", item.get("description", ""))),
        ("reference", lambda item, parent: str(item.get("ref", {}))),
        ("info", lambda item, parent: item),
    ),
)

_WAPITI_HTML = ToolHtmlSpec(
    title="Wapiti Web Vulnerability Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Category", "category"),
        ColumnSpec("Description", "description"),
        ColumnSpec("Target", "target"),
    ),
    severity_getter=lambda f: "MEDIUM",
)

_WAPITI_POLICY = ToolPolicySpec(
    rule_id_field="category",
    path_field="target",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Wapiti",
    accept_line_getter=lambda f: "",
)

WAPITI_POLICY_EXAMPLE = '''  "wapiti": {
    "accepted_findings": [
      {
        "rule_id": "cookie",
        "path_regex": "https?://.*",
        "message_regex": "Missing.*HttpOnly",
        "reason": "Legacy cookie on internal app, migration planned"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Wapiti",
    parse_spec=_WAPITI_PARSE,
    html_spec=_WAPITI_HTML,
    policy_spec=_WAPITI_POLICY,
    policy_example_snippet=WAPITI_POLICY_EXAMPLE,
    policy_key="wapiti",
)
