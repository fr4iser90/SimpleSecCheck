#!/usr/bin/env python3
"""
Android Manifest Processor for SimpleSecCheck HTML Reports
Processes Android manifest scan results and generates HTML sections
"""

import json
from pathlib import Path


def android_manifest_summary(json_path):
    """
    Extract summary from Android manifest JSON.
    
    Args:
        json_path: Path to the Android manifest JSON file
        
    Returns:
        Summary dictionary with counts
    """
    if not json_path or not Path(json_path).exists():
        return {"total_issues": 0, "high": 0, "medium": 0, "info": 0}
    
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        issues_by_severity = {"HIGH": 0, "MEDIUM": 0, "INFO": 0}
        
        for finding in data.get("findings", []):
            for issue in finding.get("security_issues", []):
                severity = issue.get("severity", "INFO")
                issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
        
        total = sum(issues_by_severity.values())
        
        return {
            "total_issues": total,
            "high": issues_by_severity.get("HIGH", 0),
            "medium": issues_by_severity.get("MEDIUM", 0),
            "info": issues_by_severity.get("INFO", 0),
            "file_count": data.get("file_count", 0)
        }
    except Exception:
        return {"total_issues": 0, "high": 0, "medium": 0, "info": 0}


def generate_android_manifest_html_section(findings):
    """
    Generate HTML section for Android manifest findings.
    
    Args:
        findings: List of Android manifest finding dictionaries
        
    Returns:
        HTML string with findings section
    """
    if not findings or len(findings) == 0:
        return ""
    
    html_parts = []
    
    html_parts.append('<div class="finding-section">')
    html_parts.append('<h2>📱 Android Manifest Security Analysis</h2>')
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
        html_parts.append('<th>Severity</th>')
        html_parts.append('<th>Issue Type</th>')
        html_parts.append('<th>Description</th>')
        html_parts.append('<th>Recommendation</th>')
        html_parts.append('</tr>')
        html_parts.append('</thead>')
        html_parts.append('<tbody>')
        
        for finding in findings:
            file_path = finding.get("file", "unknown")
            
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
                html_parts.append(f'<td><span class="severity-badge" style="background-color: {severity_color};">{severity}</span></td>')
                html_parts.append(f'<td>{issue_type}</td>')
                html_parts.append(f'<td>{description}</td>')
                html_parts.append(f'<td>{recommendation}</td>')
                html_parts.append('</tr>')
        
        html_parts.append('</tbody>')
        html_parts.append('</table>')
    
    html_parts.append('</div>')
    
    return "\n".join(html_parts)


def generate_android_manifest_html(json_path):
    """
    Main function to generate Android manifest HTML section.
    
    Args:
        json_path: Path to the Android manifest JSON file
        
    Returns:
        HTML string
    """
    if not json_path or not Path(json_path).exists():
        return ""
    
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        findings = data.get("findings", [])
        return generate_android_manifest_html_section(findings)
    except Exception:
        return ""
