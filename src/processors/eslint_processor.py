#!/usr/bin/env python3
import sys
import html
import json

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
