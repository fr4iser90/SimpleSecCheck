#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_IOS_PARSE = ParseSpec(
    items_key="findings",
    nested_items_key="security_issues",
    load_json_if_path=True,
    parent_fields=(
        ("file", "file"),
        ("bundle_id", "bundle_id"),
    ),
    fields=(
        ("severity", "severity"),
        ("type", "type"),
        ("description", "description"),
        ("recommendation", "recommendation"),
    ),
)

_IOS_HTML = ToolHtmlSpec(
    title="🍎 iOS Plist Security Analysis",
    empty_html="",
    omit_section_if_empty=True,
    columns=(
        ColumnSpec("File", "file"),
        ColumnSpec("Bundle ID", "bundle_id"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Issue Type", "type"),
        ColumnSpec("Description", "description"),
        ColumnSpec("Recommendation", "recommendation"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_IOS_POLICY = ToolPolicySpec(
    rule_id_field="type",
    path_field="file",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="ios_plist",
    accept_line_getter=lambda f: "",
)

IOS_PLIST_POLICY_EXAMPLE = '''  "ios_plist": {
    "accepted_findings": [
      {
        "rule_id": "NSAppTransportSecurity",
        "path_regex": ".*Info\\.plist$",
        "message_regex": "ATS.*exception",
        "reason": "ATS exception for legacy API endpoint only"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="ios_plist",
    parse_spec=_IOS_PARSE,
    html_spec=_IOS_HTML,
    policy_spec=_IOS_POLICY,
    policy_example_snippet=IOS_PLIST_POLICY_EXAMPLE,
    policy_key="ios_plist",
    ai_tool_name="ios_plist",
)
