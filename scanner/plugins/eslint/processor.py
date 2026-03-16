#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json
import re

def debug(msg):
    print(f"[eslint_processor] {msg}", file=sys.stderr)

def eslint_summary(eslint_json):
    findings = []
    if eslint_json and isinstance(eslint_json, list):
        for file_result in eslint_json:
            file_path = file_result.get('filePath', '')
            messages = file_result.get('messages', [])
            
            for message in messages:
                finding = {
                    'file_path': file_path,
                    'rule_id': message.get('ruleId', ''),
                    'severity': message.get('severity', 2),
                    'message': message.get('message', ''),
                    'line': message.get('line', 0),
                    'column': message.get('column', 0),
                    'end_line': message.get('endLine', 0),
                    'end_column': message.get('endColumn', 0)
                }
                
                # Skip if severity is 0 (info)
                if finding['severity'] == 0:
                    continue
                
                findings.append(finding)
    else:
        debug("No ESLint results found in JSON.")
    return findings

def generate_eslint_html_section(eslint_findings):
    html_parts = []
    html_parts.append('<h2>ESLint Security Scan</h2>')
    if eslint_findings:
        html_parts.append('<table><tr><th>File</th><th>Rule</th><th>Severity</th><th>Message</th><th>Line</th></tr>')
        for finding in eslint_findings:
            sev = finding['severity']
            sev_text = ''
            icon = ''
            if sev == 1: 
                sev_text = 'WARNING'
                icon = '⚠️'
            elif sev == 2: 
                sev_text = 'ERROR'
                icon = '🚨'
            else: 
                sev_text = 'INFO'
                icon = 'ℹ️'
            
            file_path_escaped = html.escape(str(finding.get("file_path", "")))
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            message_escaped = html.escape(str(finding.get("message", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            
            html_parts.append(f'<tr class="row-{sev_text}"><td>{file_path_escaped}</td><td>{rule_id_escaped}</td><td class="severity-{sev_text}">{icon} {sev_text}</td><td>{message_escaped}</td><td>{line_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No ESLint security issues found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_eslint_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("rule_id", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("file_path", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("message", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_eslint(finding, reason):
    return {"tool": "ESLint", "reason": reason or "Accepted by policy", "id": finding.get("rule_id", ""), "path": finding.get("file_path", ""), "line": str(finding.get("line", "")), "message": finding.get("message", "")}


def apply_eslint_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_eslint_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_eslint(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


ESLINT_POLICY_EXAMPLE = '''  "eslint": {
    "accepted_findings": [
      {
        "rule_id": "no-console",
        "path_regex": "scripts/|tools/.*\\.js$",
        "message_regex": "console",
        "reason": "Console allowed in build/script files"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="ESLint",
    summary_func=eslint_summary,
    html_func=generate_eslint_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "ESLint",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("file_path", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="eslint",
    apply_policy=apply_eslint_policy,
    policy_example_snippet=ESLINT_POLICY_EXAMPLE,
)