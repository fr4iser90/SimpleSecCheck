#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_CHECKOV_PARSE = ParseSpec(
    items_key="results.failed_checks",
    fields=(
        ("rule_id", "check_id"),
        ("check_name", "check_name"),
        ("resource", "resource"),
        ("file_path", "file_path"),
        (
            "line_number",
            lambda item, parent: (item.get("file_line_range") or [0])[0]
            if item.get("file_line_range")
            else 0,
        ),
        (
            "severity",
            lambda item, parent: "HIGH"
            if "HIGH" in str(item.get("check_name", "")) or "CRITICAL" in str(item.get("check_name", ""))
            else "MEDIUM",
        ),
        ("description", "guideline"),
        ("framework", lambda item, parent: (item.get("check_id") or item.get("rule_id", "")).split("_")[0] or "UNKNOWN"),
    ),
)

_CHECKOV_HTML = ToolHtmlSpec(
    title="Checkov Infrastructure Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No infrastructure security issues found by Checkov.</div>',
    columns=(
        ColumnSpec("Check ID", "rule_id"),
        ColumnSpec("Check Name", "check_name"),
        ColumnSpec("Framework", "framework"),
        ColumnSpec("Resource", "resource"),
        ColumnSpec("File", "file_path"),
        ColumnSpec("Severity", "severity"),
        ColumnSpec("Description", "description"),
    ),
    severity_getter="severity",
)

_CHECKOV_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="file_path",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Checkov",
    accept_line_getter=lambda f: f.get("line_number", ""),
)

CHECKOV_POLICY_EXAMPLE = '''  "checkov": {
    "accepted_findings": [
      {
        "rule_id": "CKV_K8S_1",
        "path_regex": ".*/dev/.*\\.yaml$",
        "message_regex": "image.*digest",
        "reason": "Dev namespace uses digest pinning in prod"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Checkov",
    parse_spec=_CHECKOV_PARSE,
    html_spec=_CHECKOV_HTML,
    policy_spec=_CHECKOV_POLICY,
    policy_example_snippet=CHECKOV_POLICY_EXAMPLE,
    policy_key="checkov",
)
