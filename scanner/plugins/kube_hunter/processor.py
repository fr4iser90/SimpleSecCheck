#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_KUBE_HUNTER_PARSE = ParseSpec(
    items_key="vulnerabilities",
    coerce_json_string=True,
    fields=(
        ("vid", "vid"),
        ("category", "category"),
        ("description", "description"),
        ("evidence", "evidence"),
        ("hunter", "hunter"),
        ("location", "location"),
        ("severity", "severity"),
        ("vulnerability", "vulnerability"),
        ("discovered_nodes", "discovered_nodes"),
    ),
)

_KUBE_HUNTER_HTML = ToolHtmlSpec(
    title="Kube-hunter Kubernetes Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Kubernetes vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Vulnerability", "vulnerability"),
        ColumnSpec("Severity", lambda f: str(f.get("severity", "")).upper()),
        ColumnSpec("Category", "category"),
        ColumnSpec("Location", "location"),
        ColumnSpec("Description", "description"),
    ),
    severity_getter=lambda f: str(f.get("severity", "")).upper(),
)

_KUBE_HUNTER_POLICY = ToolPolicySpec(
    rule_id_getter=lambda f: f.get("vulnerability", "") or f.get("vid", ""),
    path_getter=lambda f: f.get("location", "") or f.get("category", ""),
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Kube-hunter",
    accept_id_getter=lambda f: f.get("vulnerability", "") or f.get("vid", ""),
    accept_path_getter=lambda f: f.get("location", ""),
    accept_line_getter=lambda f: "",
)

KUBE_HUNTER_POLICY_EXAMPLE = '''  "kube_hunter": {
    "accepted_findings": [
      {
        "rule_id": "Kube Dashboard Exposed",
        "path_regex": ".*",
        "message_regex": "informational|info",
        "reason": "Dashboard behind VPN, not public"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Kube-hunter",
    parse_spec=_KUBE_HUNTER_PARSE,
    html_spec=_KUBE_HUNTER_HTML,
    policy_spec=_KUBE_HUNTER_POLICY,
    policy_example_snippet=KUBE_HUNTER_POLICY_EXAMPLE,
    policy_key="kube_hunter",
)
