#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import json
import html
import os
import re

def debug(msg):
    print(f"[bandit_processor] {msg}", file=sys.stderr)

def load_bandit_results(json_file):
    """Load Bandit JSON results file"""
    if not os.path.exists(json_file):
        debug(f"Bandit results file not found: {json_file}")
        return None
    
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        debug(f"Error loading Bandit results: {e}")
        return None

def bandit_summary(bandit_data):
    """Extract summary from Bandit results"""
    findings = []
    if bandit_data and 'results' in bandit_data:
        for result in bandit_data['results']:
            findings.append({
                'rule_id': result.get('test_id', ''),
                'test_name': result.get('test_name', ''),
                'severity': result.get('issue_severity', ''),
                'confidence': result.get('issue_confidence', ''),
                'filename': result.get('filename', ''),
                'line_number': result.get('line_number', ''),
                'code': result.get('code', ''),
                'message': result.get('issue_text', '')
            })
    else:
        debug("No Bandit results found in JSON.")
    return findings

def generate_bandit_html_section(bandit_findings):
    """Generate HTML section for Bandit findings"""
    html_parts = []
    html_parts.append('<h2>Bandit Python Security Scan</h2>')
    
    if bandit_findings:
        html_parts.append('<table><tr><th>Test ID</th><th>Severity</th><th>Confidence</th><th>File</th><th>Line</th><th>Issue</th><th>Code</th></tr>')
        for finding in bandit_findings:
            sev = finding['severity'].upper() if finding['severity'] else 'UNKNOWN'
            icon = ''
            if sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            else: icon = 'ℹ️'
            
            filename_escaped = html.escape(str(finding['filename']))
            line_escaped = html.escape(str(finding['line_number']))
            rule_id_escaped = html.escape(str(finding['rule_id']))
            message_escaped = html.escape(str(finding['message']))
            code_escaped = html.escape(str(finding['code']))
            
            html_parts.append(f'<tr><td>{rule_id_escaped}</td><td>{icon} {sev}</td><td>{finding["confidence"]}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td><td>{code_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<p>No Python security vulnerabilities found.</p>')
    
    return '\n'.join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None:
        return True
    if value is None:
        value = ""
    try:
        return re.search(pattern, str(value)) is not None
    except re.error:
        return False


def _matches_bandit_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or rule.get("rule_id") == finding.get("rule_id")
    path_ok = _matches_pattern(finding.get("filename", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("message", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_bandit(finding, reason):
    return {
        "tool": "Bandit",
        "reason": reason or "Accepted by policy",
        "id": finding.get("rule_id", ""),
        "path": finding.get("filename", ""),
        "line": finding.get("line_number", ""),
        "message": finding.get("message", ""),
    }


def apply_bandit_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_bandit_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_bandit(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


BANDIT_POLICY_EXAMPLE = '''  "bandit": {
    "accepted_findings": [
      {
        "rule_id": "B101",
        "path_regex": "tests/.*|conftest\\.py$",
        "message_regex": "assert_used",
        "reason": "Assert used only in tests, acceptable"
      }
    ]
  }'''

# Main processing logic
if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "/app/results"
    bandit_json_file = os.path.join(results_dir, 'report.json')  # Changed from bandit.json
    
    bandit_data = load_bandit_results(bandit_json_file)
    if bandit_data:
        findings = bandit_summary(bandit_data)
        html_section = generate_bandit_html_section(findings)
        print(html_section)

REPORT_PROCESSOR = ReportProcessor(
    name="Bandit",
    summary_func=bandit_summary,
    html_func=generate_bandit_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Bandit",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="bandit",
    apply_policy=apply_bandit_policy,
    policy_example_snippet=BANDIT_POLICY_EXAMPLE,
)