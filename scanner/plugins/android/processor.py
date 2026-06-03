#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_ANDROID_PARSE = ParseSpec(
    items_key="findings",
    nested_items_key="security_issues",
    load_json_if_path=True,
    parent_fields=(("file", "file"),),
    fields=(
        ("severity", "severity"),
        ("type", "type"),
        ("description", "description"),
        ("recommendation", "recommendation"),
    ),
)

_ANDROID_HTML = ToolHtmlSpec(
    title="📱 Android Manifest Security Analysis",
    empty_html="",
    omit_section_if_empty=True,
    columns=(
        ColumnSpec("File", "file"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Issue Type", "type"),
        ColumnSpec("Description", "description"),
        ColumnSpec("Recommendation", "recommendation"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_ANDROID_POLICY = ToolPolicySpec(
    rule_id_field="type",
    path_field="file",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="android_manifest",
    accept_line_getter=lambda f: "",
)

ANDROID_POLICY_EXAMPLE = '''  "android_manifest": {
    "accepted_findings": [
      {
        "rule_id": "usesCleartextTraffic",
        "path_regex": ".*debug.*AndroidManifest\\.xml$",
        "message_regex": "cleartext",
        "reason": "Cleartext only in debug build, not release"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="android_manifest",
    parse_spec=_ANDROID_PARSE,
    html_spec=_ANDROID_HTML,
    policy_spec=_ANDROID_POLICY,
    policy_example_snippet=ANDROID_POLICY_EXAMPLE,
    policy_key="android_manifest",
    ai_tool_name="android_manifest",
)
