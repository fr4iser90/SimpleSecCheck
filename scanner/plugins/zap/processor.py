#!/usr/bin/env python3
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_ZAP_PARSE = ParseSpec(
    input="dual_file",
    log_prefix="[zap_processor]",
    fields=(
        ("alert", "alert"),
        ("riskdesc", "riskdesc"),
        ("desc", "desc"),
        ("solution", "solution"),
        ("count", "count"),
    ),
    xml_nested_xpath="instances/instance",
    xml_nested_fields=(
        ("uri", "uri"),
        ("method", "method"),
        ("param", "param"),
        ("evidence", "evidence"),
    ),
)

_ZAP_HTML = ToolHtmlSpec(
    title="ZAP Web Vulnerability Scan",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>',
    columns=(),
)

REPORT_PROCESSOR = build_report_processor(
    name="ZAP",
    parse_spec=_ZAP_PARSE,
    html_spec=_ZAP_HTML,
    json_file="report.xml",
    html_file="report.html",
)
