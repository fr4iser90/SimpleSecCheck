#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import re

def debug(msg):
    print(f"[nuclei_processor] {msg}", file=sys.stderr)

def nuclei_summary(nuclei_json):
    findings = []
    if nuclei_json and isinstance(nuclei_json, list):
        for r in nuclei_json:
            finding = {
                'template_id': r.get('template-id', ''),
                'name': r.get('name', ''),
                'host': r.get('host', ''),
                'matched_at': r.get('matched-at', ''),
                'severity': r.get('info', {}).get('severity', ''),
                'description': r.get('info', {}).get('description', ''),
                'reference': r.get('info', {}).get('reference', ''),
                'tags': r.get('info', {}).get('tags', [])
            }
            findings.append(finding)
    else:
        debug("No Nuclei results found in JSON.")
    return findings

def generate_nuclei_html_section(nuclei_findings):
    html_parts = []
    html_parts.append('<h2>Nuclei Web Application Security Scan</h2>')
    if nuclei_findings:
        html_parts.append('<table><tr><th>Template</th><th>Host</th><th>Severity</th><th>Description</th></tr>')
        for finding in nuclei_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            template_id_escaped = html.escape(str(finding.get("template_id", "")))
            host_escaped = html.escape(str(finding.get("host", "")))
            sev_escaped = html.escape(str(sev))
            description_escaped = html.escape(str(finding.get("description", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{template_id_escaped}</td><td>{host_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web application vulnerabilities found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None:
        return True
    if value is None:
        value = ""
    try:
        return re.search(pattern, str(value)) is not None
    except re.error:
        return False


def _matches_nuclei_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("template_id", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("host", "") or finding.get("matched_at", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_nuclei(finding, reason):
    return {
        "tool": "Nuclei",
        "reason": reason or "Accepted by policy",
        "id": finding.get("template_id", ""),
        "path": finding.get("host", "") or finding.get("matched_at", ""),
        "line": "",
        "message": finding.get("description", ""),
    }


def apply_nuclei_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_nuclei_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_nuclei(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


NUCLEI_POLICY_EXAMPLE = '''  "nuclei": {
    "accepted_findings": [
      {
        "rule_id": "exposure-meta-tags",
        "path_regex": "https?://.*",
        "message_regex": "informational|info",
        "reason": "Informational meta tag exposure accepted"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Nuclei",
    summary_func=nuclei_summary,
    html_func=generate_nuclei_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Nuclei",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("template_id", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("host", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="nuclei",
    apply_policy=apply_nuclei_policy,
    policy_example_snippet=NUCLEI_POLICY_EXAMPLE,
)