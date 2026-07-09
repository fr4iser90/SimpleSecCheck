#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_BAAS_PARSE = ParseSpec(
    items_key="findings",
    load_json_if_path=True,
    fields=(
        ("severity", "severity"),
        ("rule_id", "rule_id"),
        ("platform", "platform"),
        ("file", "file"),
        ("line", "line"),
        ("message", "message"),
        ("recommendation", "recommendation"),
    ),
)

_BAAS_HTML = ToolHtmlSpec(
    title="🛡️ BaaS Rules & RLS Analysis",
    empty_html="",
    omit_section_if_empty=True,
    columns=(
        ColumnSpec("Platform", "platform"),
        ColumnSpec("File", "file"),
        ColumnSpec("Line", "line"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Rule", "rule_id"),
        ColumnSpec("Issue", "message"),
        ColumnSpec("Recommendation", "recommendation"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_BAAS_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="file",
    message_field="message",
    rule_id_mode="regex",
    accept_tool="baas_rules",
)

BAAS_RULES_POLICY_EXAMPLE = '''  "baas_rules": {
    "accepted_findings": [
      {
        "rule_id": "supabase_rls_open_using",
        "path_regex": ".*/supabase/migrations/.*seed.*\\\\.sql$",
        "message_regex": "USING \\\\(true\\\\)",
        "reason": "Intentional open read on public catalog table in seed migration"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="baas_rules",
    parse_spec=_BAAS_PARSE,
    html_spec=_BAAS_HTML,
    policy_spec=_BAAS_POLICY,
    policy_example_snippet=BAAS_RULES_POLICY_EXAMPLE,
    policy_key="baas_rules",
    ai_tool_name="baas_rules",
)
