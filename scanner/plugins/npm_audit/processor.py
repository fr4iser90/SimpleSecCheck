#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_NPM_AUDIT_PARSE = ParseSpec(
    items_key="vulnerabilities",
    items_from_dict_values=True,
    fields=(
        ("package", lambda item, parent: item.get("name", "")),
        ("severity", "severity"),
        ("is_direct", "isDirect"),
        ("via", "via"),
        ("effects", "effects"),
        ("range", "range"),
        ("fix_available", "fixAvailable"),
        ("dependency_path", lambda item, parent: " > ".join(item.get("nodes", []) or [])),
    ),
)

_NPM_AUDIT_HTML = ToolHtmlSpec(
    title="npm audit Dependency Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No npm dependency vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Package", "package"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Is Direct", lambda f: "Yes" if f.get("is_direct") else "No"),
        ColumnSpec("Dependency Path", "dependency_path"),
        ColumnSpec("Fix Available", lambda f: "Yes" if f.get("fix_available") else "No"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_NPM_AUDIT_POLICY = ToolPolicySpec(
    rule_id_field="package",
    path_field="dependency_path",
    message_field="severity",
    rule_id_mode="regex",
    accept_tool="npm audit",
    accept_path_getter=lambda f: f.get("dependency_path", f.get("package", "")),
    accept_line_getter=lambda f: "",
)

NPM_AUDIT_POLICY_EXAMPLE = '''  "npm_audit": {
    "accepted_findings": [
      {
        "rule_id": "minimist",
        "path_regex": ".*",
        "message_regex": "low|moderate",
        "reason": "Low/minor dependency, accepted risk"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="npm audit",
    parse_spec=_NPM_AUDIT_PARSE,
    html_spec=_NPM_AUDIT_HTML,
    policy_spec=_NPM_AUDIT_POLICY,
    policy_example_snippet=NPM_AUDIT_POLICY_EXAMPLE,
    policy_key="npm_audit",
    ai_tool_name="npm audit",
)
