#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_SEMGREP_PARSE = ParseSpec(
    items_key="results",
    fields=(
        ("rule_id", "check_id"),
        ("path", "path"),
        ("start", lambda item, parent: (item.get("start") or {}).get("line", "")),
        ("message", lambda item, parent: (item.get("extra") or {}).get("message", "")),
        ("severity", lambda item, parent: (item.get("extra") or {}).get("severity", "")),
    ),
)

_SEMGREP_HTML = ToolHtmlSpec(
    title="Semgrep Static Code Analysis",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Rule", "rule_id"),
        ColumnSpec("File", "path"),
        ColumnSpec("Line", "start"),
        ColumnSpec(
            "Message",
            lambda f: (
                (
                    f'{str(f.get("message", ""))} [Consolidated {f.get("consolidated_count")} similar findings'
                    + (f' around lines {f.get("line_span", "")}' if f.get("line_span") else "")
                    + "]"
                )
                if (f.get("consolidated_count", 1) or 1) > 1
                else str(f.get("message", ""))
            ),
        ),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_SEMGREP_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="path",
    message_field="message",
    rule_id_mode="exact",
    accept_tool="Semgrep",
    accept_line_getter=lambda f: f.get("start", ""),
)

SEMGREP_POLICY_EXAMPLE = '''  "semgrep": {
    "severity_overrides": [
      {
        "rule_id": "python.django.security.debug-true.debug-true",
        "path_regex": "settings_dev\\\\.py$",
        "new_severity": "INFO",
        "reason": "DEBUG=True is intentional for development settings"
      }
    ],
    "accepted_findings": [
      {
        "rule_id": "generic.secrets.security.hardcoded-secret.hardcoded-secret",
        "path_regex": "src/examples/.*",
        "message_regex": "just_an_example",
        "reason": "Example key in demonstration file, not a real secret"
      }
    ],
    "dedupe": {
      "enabled": true,
      "line_window": 2,
      "line_field": "start",
      "group_fields": ["rule_id", "path", "message", "severity"]
    }
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Semgrep",
    parse_spec=_SEMGREP_PARSE,
    html_spec=_SEMGREP_HTML,
    policy_spec=_SEMGREP_POLICY,
    policy_example_snippet=SEMGREP_POLICY_EXAMPLE,
    policy_key="semgrep",
)
