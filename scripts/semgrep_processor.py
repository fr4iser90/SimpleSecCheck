#!/usr/bin/env python3
import sys
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[semgrep_processor] {msg}", file=sys.stderr)

def semgrep_summary(semgrep_json):
    findings = []
    if semgrep_json and 'results' in semgrep_json:
        for r in semgrep_json['results']:
            finding = {
                'check_id': r.get('check_id', ''),
                'path': r.get('path', ''),
                'start': r.get('start', {}).get('line', ''),
                'message': r.get('extra', {}).get('message', ''),
                'severity': r.get('extra', {}).get('severity', '')
            }
            prompt = f"Explain and suggest a fix for this finding: {finding['message']} in {finding['path']} at line {finding['start']}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for semgrep finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    else:
        debug("No Semgrep results found in JSON.")
    return findings

def generate_semgrep_html_section(semgrep_findings):
    html_parts = []
    html_parts.append('<h2>Semgrep Static Code Analysis</h2>')
    if semgrep_findings:
        html_parts.append('<table><tr><th>Rule</th><th>File</th><th>Line</th><th>Message</th><th>Severity</th><th>AI Explanation</th></tr>')
        for finding in semgrep_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            ai_exp = finding.get('ai_explanation', '')
            
            check_id_escaped = html.escape(str(finding.get("check_id", "")))
            path_escaped = html.escape(str(finding.get("path", "")))
            start_escaped = html.escape(str(finding.get("start", "")))
            message_escaped = html.escape(str(finding.get("message", "")))
            sev_escaped = html.escape(str(sev))
            ai_exp_escaped = html.escape(str(ai_exp))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{check_id_escaped}</td><td>{path_escaped}</td><td>{start_escaped}</td><td>{message_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code vulnerabilities found.</div>')
    return "".join(html_parts) 