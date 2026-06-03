#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_ANCHORE_PARSE = ParseSpec(
    items_key="matches",
    fields=(
        ("PkgName", lambda item, parent: (item.get("artifact") or {}).get("name", "")),
        ("Severity", lambda item, parent: (item.get("vulnerability") or {}).get("severity", "")),
        ("VulnerabilityID", lambda item, parent: (item.get("vulnerability") or {}).get("id", "")),
        ("Title", lambda item, parent: (item.get("vulnerability") or {}).get("description", "")),
        ("Description", lambda item, parent: (item.get("vulnerability") or {}).get("description", "")),
    ),
)

_ANCHORE_HTML = ToolHtmlSpec(
    title="Anchore Container Image Vulnerability Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>',
    columns=(
        ColumnSpec("Package", "PkgName"),
        ColumnSpec("Severity", lambda f: str(f.get("Severity", "")).upper()),
        ColumnSpec("CVE", "VulnerabilityID"),
        ColumnSpec("Title", "Title"),
    ),
    severity_getter=lambda f: str(f.get("Severity", "")).upper(),
)

_ANCHORE_POLICY = ToolPolicySpec(
    rule_id_field="VulnerabilityID",
    path_field="PkgName",
    message_field="Title",
    rule_id_mode="regex",
    accept_tool="Anchore",
    accept_line_getter=lambda f: "",
)

ANCHORE_POLICY_EXAMPLE = '''  "anchore": {
    "accepted_findings": [
      {
        "rule_id": "CVE-2020-.*",
        "path_regex": "glibc|libc\\+\\+",
        "message_regex": "Negligible|Low",
        "reason": "Base image CVE, no remote exploit path"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Anchore",
    parse_spec=_ANCHORE_PARSE,
    html_spec=_ANCHORE_HTML,
    policy_spec=_ANCHORE_POLICY,
    policy_example_snippet=ANCHORE_POLICY_EXAMPLE,
    policy_key="anchore",
)
