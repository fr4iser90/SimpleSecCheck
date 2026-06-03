#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_DOCKER_BENCH_PARSE = ParseSpec(
    items_key="tests",
    nested_items_key="checks",
    coerce_json_string=True,
    parent_fields=(("group", "group"),),
    fields=(
        ("test", "test"),
        ("result", "result"),
        ("description", "test"),
        ("remediation", lambda item, parent: ""),
    ),
)

_DOCKER_BENCH_HTML = ToolHtmlSpec(
    title="Docker Bench Docker Daemon Compliance Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Docker compliance issues found.</div>',
    columns=(
        ColumnSpec("Check", "test"),
        ColumnSpec("Result", lambda f: str(f.get("result", "")).upper()),
        ColumnSpec("Group", "group"),
    ),
    severity_getter=lambda f: "INFO"
    if str(f.get("result", "")).upper() in ("INFO", "NOTE")
    else ("MEDIUM" if str(f.get("result", "")).upper() == "WARN" else "LOW"),
)

_DOCKER_BENCH_POLICY = ToolPolicySpec(
    rule_id_field="test",
    path_field="group",
    message_field="description",
    rule_id_mode="regex",
    accept_tool="Docker Bench",
    accept_line_getter=lambda f: "",
)

DOCKER_BENCH_POLICY_EXAMPLE = '''  "docker_bench": {
    "accepted_findings": [
      {
        "rule_id": "2.1",
        "path_regex": ".*",
        "message_regex": "user.*namespace",
        "reason": "User namespace enabled at daemon level"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="Docker Bench",
    parse_spec=_DOCKER_BENCH_PARSE,
    html_spec=_DOCKER_BENCH_HTML,
    policy_spec=_DOCKER_BENCH_POLICY,
    policy_example_snippet=DOCKER_BENCH_POLICY_EXAMPLE,
    policy_key="docker_bench",
)
