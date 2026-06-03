#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec, trufflehog_details
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_TRUFFLEHOG_PARSE = ParseSpec(
    root_is_list=True,
    coerce_json_string=True,
    fields=(
        ("detector", "DetectorName"),
        ("verified", "Verified"),
        ("raw", "Raw"),
        ("redacted", "Redacted"),
        ("extra_data", "ExtraData"),
        ("source_metadata", "SourceMetadata"),
        ("details", trufflehog_details),
    ),
)

_TRUFFLEHOG_HTML = ToolHtmlSpec(
    title="TruffleHog Secret Detection",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>',
    columns=(
        ColumnSpec("Detector", "detector"),
        ColumnSpec("Verified", lambda f: "Yes" if f.get("verified") else "No"),
        ColumnSpec(
            "Details",
            lambda f: f.get("details", "")
            or (
                (f.get("extra_data") or {}).get("message", "")
                if isinstance(f.get("extra_data"), dict)
                else ""
            ),
        ),
    ),
    severity_getter=lambda f: "HIGH" if f.get("verified") else "MEDIUM",
)

_TRUFFLEHOG_POLICY = ToolPolicySpec(
    rule_id_field="detector",
    path_field="details",
    message_field="details",
    rule_id_mode="regex",
    accept_tool="TruffleHog",
    accept_line_getter=lambda f: "",
)

TRUFFLEHOG_POLICY_EXAMPLE = '''  "trufflehog": {
    "accepted_findings": [
      {
        "rule_id": "AWS",
        "path_regex": ".*\\.example\\.com.*|docs/.*",
        "message_regex": "AKIA.*example",
        "reason": "Example/placeholder AWS key in docs"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="TruffleHog",
    parse_spec=_TRUFFLEHOG_PARSE,
    html_spec=_TRUFFLEHOG_HTML,
    policy_spec=_TRUFFLEHOG_POLICY,
    policy_example_snippet=TRUFFLEHOG_POLICY_EXAMPLE,
    policy_key="trufflehog",
)
