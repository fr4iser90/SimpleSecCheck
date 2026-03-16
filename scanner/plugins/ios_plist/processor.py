#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
"""
iOS Plist Processor for SimpleSecCheck HTML Reports
Processes iOS plist scan results and generates HTML sections
"""

import json
import re
from pathlib import Path


def ios_plist_summary(json_path):
    """
    Extract findings from iOS plist JSON.
    
    Args:
        json_path: Path to the iOS plist JSON file
        
    Returns:
        List of finding dictionaries with 'severity' field for executive summary
    """
    if not json_path or not Path(json_path).exists():
        return []
    
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        findings = []
        
        # Convert each security issue into a finding for executive summary
        for plist_file in data.get("findings", []):
            for issue in plist_file.get("security_issues", []):
                finding = {
                    "severity": issue.get("severity", "INFO"),
                    "type": issue.get("type", "unknown"),
                    "description": issue.get("description", ""),
                    "file": plist_file.get("file", "unknown")
                }
                findings.append(finding)
        
        return findings
    except Exception:
        return []


def generate_ios_plist_html_section(findings):
    """
    Generate HTML section for iOS plist findings.
    
    Args:
        findings: List of iOS plist finding dictionaries
        
    Returns:
        HTML string with findings section
    """
    if not findings or len(findings) == 0:
        return ""
    
    html_parts = []
    
    html_parts.append('<div class="finding-section">')
    html_parts.append('<h2>🍎 iOS Plist Security Analysis</h2>')
    html_parts.append('<div class="summary-box">')
    html_parts.append(f'<p><b>Files Analyzed:</b> {len(findings)}</p>')
    
    total_issues = sum(len(f.get("security_issues", [])) for f in findings)
    if total_issues > 0:
        html_parts.append(f'<p><b>Security Issues Found:</b> {total_issues}</p>')
    else:
        html_parts.append('<p><b>Status:</b> ✅ No security issues detected</p>')
    
    html_parts.append('</div>')
    
    if total_issues > 0:
        html_parts.append('<table class="finding-table">')
        html_parts.append('<thead>')
        html_parts.append('<tr>')
        html_parts.append('<th>File</th>')
        html_parts.append('<th>Bundle ID</th>')
        html_parts.append('<th>Severity</th>')
        html_parts.append('<th>Issue Type</th>')
        html_parts.append('<th>Description</th>')
        html_parts.append('<th>Recommendation</th>')
        html_parts.append('</tr>')
        html_parts.append('</thead>')
        html_parts.append('<tbody>')
        
        for finding in findings:
            file_path = finding.get("file", "unknown")
            bundle_id = finding.get("bundle_id", "unknown")
            
            for issue in finding.get("security_issues", []):
                severity = issue.get("severity", "INFO")
                issue_type = issue.get("type", "unknown")
                description = issue.get("description", "")
                recommendation = issue.get("recommendation", "")
                
                # Color coding based on severity
                severity_class = severity.lower()
                severity_color = {
                    "high": "#dc3545",
                    "medium": "#ffc107",
                    "info": "#17a2b8"
                }.get(severity_class, "#6c757d")
                
                html_parts.append('<tr>')
                html_parts.append(f'<td>{file_path}</td>')
                html_parts.append(f'<td>{bundle_id}</td>')
                html_parts.append(f'<td><span class="severity-badge" style="background-color: {severity_color};">{severity}</span></td>')
                html_parts.append(f'<td>{issue_type}</td>')
                html_parts.append(f'<td>{description}</td>')
                html_parts.append(f'<td>{recommendation}</td>')
                html_parts.append('</tr>')
        
        html_parts.append('</tbody>')
        html_parts.append('</table>')
    
    html_parts.append('</div>')
    
    return "\n".join(html_parts)


def generate_ios_plist_html(json_path):
    """
    Main function to generate iOS plist HTML section.
    
    Args:
        json_path: Path to the iOS plist JSON file
        
    Returns:
        HTML string
    """
    if not json_path or not Path(json_path).exists():
        return ""
    
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        findings = data.get("findings", [])
        return generate_ios_plist_html_section(findings)
    except Exception:
        return ""

def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_ios_plist_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("type", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("file", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_ios_plist(finding, reason):
    return {"tool": "ios_plist", "reason": reason or "Accepted by policy", "id": finding.get("type", ""), "path": finding.get("file", ""), "line": "", "message": finding.get("description", "")}


def apply_ios_plist_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_ios_plist_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_ios_plist(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


IOS_PLIST_POLICY_EXAMPLE = '''  "ios_plist": {
    "accepted_findings": [
      {
        "rule_id": "NSAppTransportSecurity",
        "path_regex": ".*Info\\.plist$",
        "message_regex": "ATS.*exception",
        "reason": "ATS exception for legacy API endpoint only"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="ios_plist",
    summary_func=ios_plist_summary,
    html_func=generate_ios_plist_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "ios_plist",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("type", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="ios_plist",
    apply_policy=apply_ios_plist_policy,
    policy_example_snippet=IOS_PLIST_POLICY_EXAMPLE,
)