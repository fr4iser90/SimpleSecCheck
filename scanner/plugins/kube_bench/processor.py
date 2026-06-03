#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_KUBE_BENCH_PARSE = ParseSpec(
    items_key="tests",
    nested_items_key="checks",
    coerce_json_string=True,
    parent_fields=(("group", "group"),),
    fields=(
        ("id", "id"),
        ("description", "description"),
        ("state", "state"),
        ("remediation", "remediation"),
    ),
)

_KUBE_BENCH_HTML = ToolHtmlSpec(
    title="Kube-bench Kubernetes Compliance Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Kubernetes compliance issues found.</div>',
    columns=(
        ColumnSpec("Check ID", "id"),
        ColumnSpec("State", "state"),
        ColumnSpec("Group", "group"),
        ColumnSpec("Description", "description"),
        ColumnSpec("Remediation", "remediation"),
    ),
    severity_getter=lambda f: str(f.get("state", "WARN")).upper(),
)

_KUBE_BENCH_POLICY = ToolPolicySpec(
    rule_id_field="id",
    path_field="group",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Kube-bench",
    accept_line_getter=lambda f: "",
)

KUBE_BENCH_POLICY_EXAMPLE = '''  "kube_bench": {
    "accepted_findings": [
      {
        "rule_id": "1.2.1",
        "path_regex": "control-plane|master",
        "message_regex": "anonymous.*auth",
        "reason": "Anonymous auth disabled via admission controller"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Kube-bench",
    parse_spec=_KUBE_BENCH_PARSE,
    html_spec=_KUBE_BENCH_HTML,
    policy_spec=_KUBE_BENCH_POLICY,
    policy_example_snippet=KUBE_BENCH_POLICY_EXAMPLE,
    policy_key="kube_bench",
)
