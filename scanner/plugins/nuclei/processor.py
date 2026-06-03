#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_NUCLEI_PARSE = ParseSpec(
    root_is_list=True,
    fields=(
        ("template_id", "template-id"),
        ("name", "name"),
        ("host", "host"),
        ("matched_at", "matched-at"),
        ("severity", lambda item, parent: (item.get("info") or {}).get("severity", "")),
        ("description", lambda item, parent: (item.get("info") or {}).get("description", "")),
        ("reference", lambda item, parent: (item.get("info") or {}).get("reference", "")),
        ("tags", lambda item, parent: (item.get("info") or {}).get("tags", [])),
    ),
)

_NUCLEI_HTML = ToolHtmlSpec(
    title="Nuclei Web Application Security Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web application vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Template", "template_id"),
        ColumnSpec("Host", "host"),
        ColumnSpec("Severity", "severity"),
        ColumnSpec("Description", "description"),
    ),
    severity_getter="severity",
)

_NUCLEI_POLICY = ToolPolicySpec(
    rule_id_field="template_id",
    path_getter=lambda f: f.get("host", "") or f.get("matched_at", ""),
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Nuclei",
    accept_path_getter=lambda f: f.get("host", "") or f.get("matched_at", ""),
    accept_line_getter=lambda f: "",
)

NUCLEI_POLICY_EXAMPLE = '''  "nuclei": {
    "accepted_findings": [
      {
        "rule_id": "exposure-meta-tags",
        "path_regex": "https?://.*",
        "message_regex": "informational|info",
        "reason": "Informational meta tag exposure accepted"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Nuclei",
    parse_spec=_NUCLEI_PARSE,
    html_spec=_NUCLEI_HTML,
    policy_spec=_NUCLEI_POLICY,
    policy_example_snippet=NUCLEI_POLICY_EXAMPLE,
    policy_key="nuclei",
)
