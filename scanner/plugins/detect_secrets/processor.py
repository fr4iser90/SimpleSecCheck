#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_DETECT_SECRETS_PARSE = ParseSpec(
    items_key="results",
    dict_key_parent_field="filename",
    coerce_json_string=True,
    fields=(
        ("filename", "parent.filename"),
        ("line_number", "line_number"),
        ("type", "type"),
        ("hashed_secret", "hashed_secret"),
        ("is_secret", "is_secret"),
        ("is_verified", "is_verified"),
    ),
)

_DETECT_SECRETS_HTML = ToolHtmlSpec(
    title="Detect-secrets Secret Detection",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>',
    columns=(
        ColumnSpec("Type", "type"),
        ColumnSpec("File", "filename"),
        ColumnSpec("Line", "line_number"),
        ColumnSpec("Verified", lambda f: ("Yes" if f.get("is_verified") else "No")),
    ),
    severity_getter=lambda f: "HIGH" if f.get("is_verified") else "MEDIUM",
)

_DETECT_SECRETS_POLICY = ToolPolicySpec(
    rule_id_field="type",
    path_field="filename",
    message_field="type",
    rule_id_mode="regex",
    accept_tool="Detect-secrets",
    accept_line_getter=lambda f: f.get("line_number", ""),
)

DETECT_SECRETS_POLICY_EXAMPLE = '''  "detect_secrets": {
    "accepted_findings": [
      {
        "rule_id": "Private Key",
        "path_regex": "tests/fixtures/.*\\.pem$",
        "reason": "Test fixture keys, not used at runtime"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Detect-secrets",
    parse_spec=_DETECT_SECRETS_PARSE,
    html_spec=_DETECT_SECRETS_HTML,
    policy_spec=_DETECT_SECRETS_POLICY,
    policy_example_snippet=DETECT_SECRETS_POLICY_EXAMPLE,
    policy_key="detect_secrets",
)
