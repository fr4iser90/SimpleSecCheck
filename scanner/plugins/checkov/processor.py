#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import re

def debug(msg):
    print(f"[checkov_processor] {msg}", file=sys.stderr)

def checkov_summary(checkov_json):
    findings = []
    if checkov_json and isinstance(checkov_json, dict):
        # Handle Checkov JSON format
        results = checkov_json.get('results', {})
        failed_checks = results.get('failed_checks', [])
        
        for check in failed_checks:
            finding = {
                'rule_id': check.get('rule_id', ''),
                'check_name': check.get('check_name', ''),
                'resource': check.get('resource', ''),
                'file_path': check.get('file_path', ''),
                'line_number': check.get('file_line_range', [0])[0] if check.get('file_line_range') else 0,
                'severity': 'HIGH' if 'HIGH' in check.get('check_name', '') or 'CRITICAL' in check.get('check_name', '') else 'MEDIUM',
                'description': check.get('guideline', ''),
                'code_block': check.get('code_block', []),
                'fix': check.get('code_block', []),
                'framework': check.get('rule_id', '').split('_')[0] if check.get('rule_id', '') else 'UNKNOWN'
            }
            
            findings.append(finding)
    else:
        debug("No Checkov results found in JSON.")
    return findings

def generate_checkov_html_section(checkov_findings):
    html_parts = []
    html_parts.append('<h2>Checkov Infrastructure Security Scan</h2>')
    if checkov_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>Check Name</th><th>Framework</th><th>Resource</th><th>File</th><th>Severity</th><th>Description</th></tr>')
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            check_name_escaped = html.escape(str(finding.get("check_name", "")))
            framework_escaped = html.escape(str(finding.get("framework", "UNKNOWN")))
            resource_escaped = html.escape(str(finding.get("resource", "")))
            file_path_escaped = html.escape(str(finding.get("file_path", "")))
            sev_escaped = html.escape(str(sev))
            desc_escaped = html.escape(str(finding.get("description", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{rule_id_escaped}</td><td>{check_name_escaped}</td><td>{framework_escaped}</td><td>{resource_escaped}</td><td>{file_path_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{desc_escaped}</td></tr>')
        html_parts.append('</table>')
        
        # Add summary statistics
        severity_counts = {}
        framework_counts = {}
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            framework = finding.get('framework', 'UNKNOWN')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            framework_counts[framework] = framework_counts.get(framework, 0) + 1
        
        html_parts.append('<div class="summary-stats">')
        html_parts.append('<h3>Security Issue Summary</h3>')
        html_parts.append('<ul>')
        for sev, count in severity_counts.items():
            html_parts.append(f'<li>{sev}: {count} issues</li>')
        html_parts.append(f'<li><strong>Total: {len(checkov_findings)} infrastructure security issues</strong></li>')
        html_parts.append('</ul>')
        
        html_parts.append('<h3>Issues by Framework</h3>')
        html_parts.append('<ul>')
        for framework, count in framework_counts.items():
            html_parts.append(f'<li>{framework}: {count} issues</li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No infrastructure security issues found by Checkov.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_checkov_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("rule_id", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("file_path", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_checkov(finding, reason):
    return {"tool": "Checkov", "reason": reason or "Accepted by policy", "id": finding.get("rule_id", ""), "path": finding.get("file_path", ""), "line": str(finding.get("line_number", "")), "message": finding.get("description", "")}


def apply_checkov_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_checkov_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_checkov(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


CHECKOV_POLICY_EXAMPLE = '''  "checkov": {
    "accepted_findings": [
      {
        "rule_id": "CKV_K8S_1",
        "path_regex": ".*/dev/.*\\.yaml$",
        "message_regex": "image.*digest",
        "reason": "Dev namespace uses digest pinning in prod"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Checkov",
    summary_func=checkov_summary,
    html_func=generate_checkov_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Checkov",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("file_path", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", f.get("line_number", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="checkov",
    apply_policy=apply_checkov_policy,
    policy_example_snippet=CHECKOV_POLICY_EXAMPLE,
)