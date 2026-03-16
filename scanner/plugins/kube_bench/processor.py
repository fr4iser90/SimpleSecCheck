#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

import re

def debug(msg):
    print(f"[kube_bench_processor] {msg}", file=sys.stderr)

def kube_bench_summary(kube_bench_json):
    findings = []
    if kube_bench_json and isinstance(kube_bench_json, dict):
        # Parse Kube-bench JSON output
        checks_records = kube_bench_json.get('tests', [])
        for check_group in checks_records:
            group_name = check_group.get('group', '')
            group_summary = check_group.get('summary', {})
            
            # Extract check results
            for test in check_group.get('checks', []):
                finding = {
                    'id': test.get('id', ''),
                    'description': test.get('description', ''),
                    'state': test.get('state', ''),
                    'group': group_name,
                    'remediation': test.get('remediation', '')
                }
                findings.append(finding)
    elif kube_bench_json and isinstance(kube_bench_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(kube_bench_json)
            if isinstance(data, dict):
                checks_records = data.get('tests', [])
                for check_group in checks_records:
                    group_name = check_group.get('group', '')
                    
                    # Extract check results
                    for test in check_group.get('checks', []):
                        finding = {
                            'id': test.get('id', ''),
                            'description': test.get('description', ''),
                            'state': test.get('state', ''),
                            'group': group_name,
                            'remediation': test.get('remediation', '')
                        }
                        findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse Kube-bench JSON as string.")
    else:
        debug("No Kube-bench results found in JSON.")
    return findings

def generate_kube_bench_html_section(kube_bench_findings):
    html_parts = []
    html_parts.append('<h2>Kube-bench Kubernetes Compliance Scan</h2>')
    if kube_bench_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>State</th><th>Group</th><th>Description</th><th>Remediation</th></tr>')
        for finding in kube_bench_findings:
            rule_id_escaped = html.escape(str(finding.get('id', '')))
            state_escaped = html.escape(str(finding.get('state', '')))
            group_escaped = html.escape(str(finding.get('group', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            remediation_escaped = html.escape(str(finding.get('remediation', '')))
            
            # Color-code state
            state_class = "sev-MEDIUM"
            icon = '⚠️'
            if finding.get('state', '').upper() == 'PASS':
                state_class = "sev-PASSED"
                icon = '✅'
            elif finding.get('state', '').upper() == 'WARN':
                state_class = "sev-MEDIUM"
                icon = '⚠️'
            elif finding.get('state', '').upper() == 'FAIL':
                state_class = "sev-HIGH"
                icon = '🚨'
            
            html_parts.append(f'<tr class="row-{finding.get("state", "WARN").upper()}"><td>{rule_id_escaped}</td><td class="{state_class}">{icon} {state_escaped}</td><td>{group_escaped}</td><td>{description_escaped}</td><td>{remediation_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Kubernetes compliance issues found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_kube_bench_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("id", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("group", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_kube_bench(finding, reason):
    return {"tool": "Kube-bench", "reason": reason or "Accepted by policy", "id": finding.get("id", ""), "path": finding.get("group", ""), "line": "", "message": finding.get("description", "")}


def apply_kube_bench_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_kube_bench_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_kube_bench(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


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

REPORT_PROCESSOR = ReportProcessor(
    name="Kube-bench",
    summary_func=kube_bench_summary,
    html_func=generate_kube_bench_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Kube-bench",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("group", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="kube_bench",
    apply_policy=apply_kube_bench_policy,
    policy_example_snippet=KUBE_BENCH_POLICY_EXAMPLE,
)