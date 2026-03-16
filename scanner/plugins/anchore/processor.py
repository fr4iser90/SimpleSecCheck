#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import re

def debug(msg):
    print(f"[anchore_processor] {msg}", file=sys.stderr)

def anchore_summary(anchore_json):
    vulns = []
    if anchore_json and 'matches' in anchore_json:
        for match in anchore_json['matches']:
            vulns.append({
                'PkgName': match.get('artifact', {}).get('name', ''),
                'Severity': match.get('vulnerability', {}).get('severity', ''),
                'VulnerabilityID': match.get('vulnerability', {}).get('id', ''),
                'Title': match.get('vulnerability', {}).get('description', ''),
                'Description': match.get('vulnerability', {}).get('description', '')
            })
    else:
        debug("No Anchore results found in JSON.")
    return vulns

def generate_anchore_html_section(anchore_vulns):
    html_parts = []
    html_parts.append('<h2>Anchore Container Image Vulnerability Scan</h2>')
    
    # Check if there's a note about setup requirements
    if not anchore_vulns or (anchore_vulns and len(anchore_vulns) == 0):
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>')
    elif anchore_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in anchore_vulns:
            sev = v.get('Severity', 'UNKNOWN').upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            # Basic HTML escaping
            pkg_name_escaped = sev_escaped = vuln_id_escaped = title_escaped = ""
            try:
                import html
                pkg_name_escaped = html.escape(str(v.get("PkgName", "")))
                sev_escaped = html.escape(str(sev))
                vuln_id_escaped = html.escape(str(v.get("VulnerabilityID", "")))
                title_escaped = html.escape(str(v.get("Title", "")))
            except ImportError:
                pkg_name_escaped = str(v.get("PkgName", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                vuln_id_escaped = str(v.get("VulnerabilityID", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(v.get("Title", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{pkg_name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{vuln_id_escaped}</td><td>{title_escaped}</td></tr>')
        html_parts.append('</table>')
    
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_anchore_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("VulnerabilityID", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("PkgName", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("Title", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_anchore(finding, reason):
    return {"tool": "Anchore", "reason": reason or "Accepted by policy", "id": finding.get("VulnerabilityID", ""), "path": finding.get("PkgName", ""), "line": "", "message": finding.get("Title", "")}


def apply_anchore_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_anchore_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_anchore(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


ANCHORE_POLICY_EXAMPLE = '''  "anchore": {
    "accepted_findings": [
      {
        "rule_id": "CVE-2020-.*",
        "path_regex": "glibc|libc\\+\\+",
        "message_regex": "Negligible|Low",
        "reason": "Base image CVE, no remote exploit path"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Anchore",
    summary_func=anchore_summary,
    html_func=generate_anchore_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Anchore",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("VulnerabilityID", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("PkgName", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", f.get("Title", ""))))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="anchore",
    apply_policy=apply_anchore_policy,
    policy_example_snippet=ANCHORE_POLICY_EXAMPLE,
)