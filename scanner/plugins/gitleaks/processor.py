#!/usr/bin/env python3
from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.finding_parse_spec import ParseSpec
from scanner.output.findings_html_renderer import ColumnSpec, ToolHtmlSpec
from scanner.output.processor_builder import build_report_processor

_GITLEAKS_PARSE = ParseSpec(
    root_is_list=True,
    coerce_json_string=True,
    fields=(
        ("rule_id", "RuleID"),
        ("description", "Description"),
        ("file", "File"),
        ("line", "StartLine"),
        ("secret", "Secret"),
        ("commit", "Commit"),
        ("author", "Author"),
        ("date", "Date"),
    ),
)

_GITLEAKS_HTML = ToolHtmlSpec(
    title="GitLeaks Secret Detection",
    empty_html='<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>',
    columns=(
        ColumnSpec("Rule ID", "rule_id"),
        ColumnSpec("File", "file"),
        ColumnSpec("Line", "line"),
        ColumnSpec("Description", "description"),
    ),
)

_GITLEAKS_POLICY = ToolPolicySpec(
    rule_id_field="rule_id",
    path_field="file",
    message_field="description",
    rule_id_mode="exact",
    policy_rule_id_key="rule_id",
    policy_path_key="file_regex",
    policy_message_key="description_regex",
    accept_tool="GitLeaks",
)

GITLEAKS_POLICY_EXAMPLE = '''  "gitleaks": {
    "accepted_findings": [
      {
        "rule_id": "generic-api-key",
        "file_regex": "tests/.*",
        "description_regex": "test.*key",
        "reason": "Test files contain example keys, not real secrets"
      }
    ]
  }'''

REPORT_PROCESSOR = build_report_processor(
    name="GitLeaks",
    parse_spec=_GITLEAKS_PARSE,
    html_spec=_GITLEAKS_HTML,
    policy_spec=_GITLEAKS_POLICY,
    policy_example_snippet=GITLEAKS_POLICY_EXAMPLE,
    policy_key="gitleaks",
)
