#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_TERRAFORM_PARSE = ParseSpec(
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
    ),
)

_TERRAFORM_HTML = ToolHtmlSpec(
    title="Checkov Terraform Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Terraform security issues found by Checkov.</div>',
    columns=(
        ColumnSpec("Check ID", "rule_id"),
        ColumnSpec("Check Name", "check_name"),
        ColumnSpec("Resource", "resource"),
        ColumnSpec("File", "file_path"),
        ColumnSpec("Severity", "severity"),
        ColumnSpec("Description", "description"),
    ),
    severity_getter="severity",
)

_TERRAFORM_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="file_path",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Terraform Checkov",
    accept_line_getter=lambda f: f.get("line_number", ""),
)

TERRAFORM_POLICY_EXAMPLE = '''  "terraform_checkov": {
    "accepted_findings": [
      {
        "rule_id": "CKV_AWS_20",
        "path_regex": "modules/s3.*\\.tf$",
        "message_regex": "bucket.*encryption",
        "reason": "S3 encryption enforced at org level"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Terraform Checkov",
    parse_spec=_TERRAFORM_PARSE,
    html_spec=_TERRAFORM_HTML,
    policy_spec=_TERRAFORM_POLICY,
    policy_example_snippet=TERRAFORM_POLICY_EXAMPLE,
    policy_key="terraform_checkov",
    ai_tool_name="Terraform Checkov",
)
