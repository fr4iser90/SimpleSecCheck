#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

import re

def debug(msg):
    print(f"[docker_bench_processor] {msg}", file=sys.stderr)

def docker_bench_summary(docker_bench_json):
    findings = []
    if docker_bench_json and isinstance(docker_bench_json, dict):
        # Parse Docker Bench JSON output
        checks_records = docker_bench_json.get('tests', [])
        for check_group in checks_records:
            group_name = check_group.get('group', 'Docker Compliance')
            group_summary = check_group.get('summary', {})
            
            # Extract check results
            for test in check_group.get('checks', []):
                finding = {
                    'test': test.get('test', ''),
                    'result': test.get('result', ''),
                    'group': group_name,
                    'description': test.get('test', ''),
                    'remediation': ''
                }
                findings.append(finding)
    elif docker_bench_json and isinstance(docker_bench_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(docker_bench_json)
            if isinstance(data, dict):
                checks_records = data.get('tests', [])
                for check_group in checks_records:
                    group_name = check_group.get('group', 'Docker Compliance')
                    
                    # Extract check results
                    for test in check_group.get('checks', []):
                        finding = {
                            'test': test.get('test', ''),
                            'result': test.get('result', ''),
                            'group': group_name,
                            'description': test.get('test', ''),
                            'remediation': ''
                        }
                        findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse Docker Bench JSON as string.")
    else:
        debug("No Docker Bench results found in JSON.")
    return findings

def generate_docker_bench_html_section(docker_bench_findings):
    html_parts = []
    html_parts.append('<h2>Docker Bench Docker Daemon Compliance Scan</h2>')
    if docker_bench_findings:
        html_parts.append('<table><tr><th>Check</th><th>Result</th><th>Group</th></tr>')
        for finding in docker_bench_findings:
            test_escaped = html.escape(str(finding.get('test', '')))
            result_escaped = html.escape(str(finding.get('result', '')))
            group_escaped = html.escape(str(finding.get('group', '')))
            
            # Color-code result
            result_class = "sev-MEDIUM"
            icon = '✅'
            if finding.get('result', '').upper() == 'PASS':
                result_class = "sev-PASSED"
                icon = '✅'
            elif finding.get('result', '').upper() == 'WARN':
                result_class = "sev-MEDIUM"
                icon = '⚠️'
            elif finding.get('result', '').upper() == 'INFO':
                result_class = "sev-LOW"
                icon = 'ℹ️'
            elif finding.get('result', '').upper() == 'NOTE':
                result_class = "sev-LOW"
                icon = 'ℹ️'
            
            html_parts.append(f'<tr class="row-{finding.get("result", "WARN").upper()}"><td>{test_escaped}</td><td class="{result_class}">{icon} {result_escaped}</td><td>{group_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Docker compliance issues found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_docker_bench_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("test", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("group", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_docker_bench(finding, reason):
    return {"tool": "Docker Bench", "reason": reason or "Accepted by policy", "id": finding.get("test", ""), "path": finding.get("group", ""), "line": "", "message": finding.get("description", "")}


def apply_docker_bench_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_docker_bench_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_docker_bench(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


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

REPORT_PROCESSOR = ReportProcessor(
    name="Docker Bench",
    summary_func=docker_bench_summary,
    html_func=generate_docker_bench_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Docker Bench",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("test", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("group", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="docker_bench",
    apply_policy=apply_docker_bench_policy,
    policy_example_snippet=DOCKER_BENCH_POLICY_EXAMPLE,
)