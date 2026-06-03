#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_NIKTO_PARSE = ParseSpec(
    items_key="scan_details",
    dict_key_parent_field="hostname",
    nested_items_key="items",
    parent_fields=(
        ("hostname", "hostname"),
        ("target_ip", "target_ip"),
        ("host_ip", "host_ip"),
    ),
    fields=(
        ("osvdb", "osvdb"),
        ("osvdb_link", "osvdb_link"),
        ("name", "name"),
        ("description", "description"),
        ("full_name", "full_name"),
    ),
)

_NIKTO_HTML = ToolHtmlSpec(
    title="Nikto Web Server Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>',
    columns=(
        ColumnSpec("Finding", "name"),
        ColumnSpec("Description", "description"),
        ColumnSpec("Host", "hostname"),
    ),
    severity_getter=lambda f: "MEDIUM",
)

_NIKTO_POLICY = ToolPolicySpec(
    rule_id_field="name",
    path_getter=lambda f: f.get("hostname", "") or f.get("target_ip", ""),
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Nikto",
    accept_path_getter=lambda f: f.get("hostname", "") or f.get("target_ip", ""),
    accept_line_getter=lambda f: "",
)

NIKTO_POLICY_EXAMPLE = '''  "nikto": {
    "accepted_findings": [
      {
        "rule_id": "Server.*disclosure",
        "path_regex": ".*",
        "message_regex": "X-Powered-By|Server:",
        "reason": "Server header stripped at reverse proxy"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Nikto",
    parse_spec=_NIKTO_PARSE,
    html_spec=_NIKTO_HTML,
    policy_spec=_NIKTO_POLICY,
    policy_example_snippet=NIKTO_POLICY_EXAMPLE,
    policy_key="nikto",
)
