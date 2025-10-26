#!/usr/bin/env python3
import sys
import json
import xml.etree.ElementTree as ET

def debug(msg):
    print(f"[owasp_dependency_check_processor] {msg}", file=sys.stderr)

def owasp_dependency_check_summary(owasp_dc_json):
    """Extract vulnerability summary from OWASP Dependency Check JSON report"""
    vulnerabilities = []
    
    if not owasp_dc_json:
        debug("No OWASP Dependency Check results found in JSON.")
        return vulnerabilities
    
    try:
        # OWASP Dependency Check JSON structure
        if 'dependencies' in owasp_dc_json:
            for dependency in owasp_dc_json['dependencies']:
                dep_name = dependency.get('fileName', 'Unknown')
                dep_version = dependency.get('version', 'Unknown')
                
                # Process vulnerabilities for this dependency
                if 'vulnerabilities' in dependency:
                    for vuln in dependency['vulnerabilities']:
                        vulnerabilities.append({
                            'Dependency': f"{dep_name} ({dep_version})",
                            'Severity': vuln.get('severity', 'UNKNOWN'),
                            'CVE': vuln.get('name', ''),
                            'Title': vuln.get('title', ''),
                            'Description': vuln.get('description', ''),
                            'CVSS': vuln.get('cvssScore', 0.0),
                            'CVSS_Vector': vuln.get('cvssVector', ''),
                            'References': vuln.get('references', [])
                        })
                        
        debug(f"Found {len(vulnerabilities)} OWASP Dependency Check vulnerabilities")
        
    except Exception as e:
        debug(f"Error parsing OWASP Dependency Check JSON: {e}")
        
    return vulnerabilities

def generate_owasp_dependency_check_html_section(owasp_dc_vulns):
    """Generate HTML section for OWASP Dependency Check vulnerabilities"""
    html_parts = []
    html_parts.append('<h2>OWASP Dependency Check - Dependency Vulnerabilities</h2>')
    
    if owasp_dc_vulns:
        html_parts.append('<table><tr><th>Dependency</th><th>Severity</th><th>CVE</th><th>CVSS Score</th><th>Title</th></tr>')
        
        for vuln in owasp_dc_vulns:
            sev = vuln['Severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            else: icon = '❓'
            
            # Basic HTML escaping
            dep_escaped = sev_escaped = cve_escaped = title_escaped = ""
            try:
                import html
                dep_escaped = html.escape(str(vuln["Dependency"]))
                sev_escaped = html.escape(str(sev))
                cve_escaped = html.escape(str(vuln["CVE"]))
                title_escaped = html.escape(str(vuln["Title"]))
            except ImportError:
                dep_escaped = str(vuln["Dependency"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                cve_escaped = str(vuln["CVE"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(vuln["Title"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            cvss_score = vuln.get('CVSS', 0.0)
            cvss_class = ""
            if cvss_score >= 9.0: cvss_class = "cvss-critical"
            elif cvss_score >= 7.0: cvss_class = "cvss-high"
            elif cvss_score >= 4.0: cvss_class = "cvss-medium"
            else: cvss_class = "cvss-low"
            
            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{dep_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{cve_escaped}</td><td class="{cvss_class}">{cvss_score}</td><td>{title_escaped}</td></tr>')
        
        html_parts.append('</table>')
        
        # Add summary statistics
        critical_count = sum(1 for v in owasp_dc_vulns if v['Severity'].upper() == 'CRITICAL')
        high_count = sum(1 for v in owasp_dc_vulns if v['Severity'].upper() == 'HIGH')
        medium_count = sum(1 for v in owasp_dc_vulns if v['Severity'].upper() == 'MEDIUM')
        low_count = sum(1 for v in owasp_dc_vulns if v['Severity'].upper() == 'LOW')
        
        html_parts.append(f'<div class="vulnerability-summary">')
        html_parts.append(f'<h3>Vulnerability Summary</h3>')
        html_parts.append(f'<ul>')
        if critical_count > 0: html_parts.append(f'<li class="severity-CRITICAL">🚨 Critical: {critical_count}</li>')
        if high_count > 0: html_parts.append(f'<li class="severity-HIGH">🚨 High: {high_count}</li>')
        if medium_count > 0: html_parts.append(f'<li class="severity-MEDIUM">⚠️ Medium: {medium_count}</li>')
        if low_count > 0: html_parts.append(f'<li class="severity-LOW">ℹ️ Low: {low_count}</li>')
        html_parts.append(f'</ul>')
        html_parts.append(f'</div>')
        
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No dependency vulnerabilities found.</div>')
    
    return "".join(html_parts)

def parse_owasp_dependency_check_xml(xml_path):
    """Parse OWASP Dependency Check XML report for additional details"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        vulnerabilities = []
        
        # Parse XML structure
        for dependency in root.findall('.//dependency'):
            dep_name = dependency.get('fileName', 'Unknown')
            dep_version = dependency.get('version', 'Unknown')
            
            for vuln in dependency.findall('.//vulnerability'):
                vulnerabilities.append({
                    'Dependency': f"{dep_name} ({dep_version})",
                    'Severity': vuln.get('severity', 'UNKNOWN'),
                    'CVE': vuln.get('name', ''),
                    'Title': vuln.findtext('title', ''),
                    'Description': vuln.findtext('description', ''),
                    'CVSS': float(vuln.get('cvssScore', 0.0)),
                    'CVSS_Vector': vuln.get('cvssVector', '')
                })
        
        return vulnerabilities
        
    except Exception as e:
        debug(f"Error parsing OWASP Dependency Check XML: {e}")
        return []

if __name__ == "__main__":
    # Test the processor
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            vulns = owasp_dependency_check_summary(data)
            html = generate_owasp_dependency_check_html_section(vulns)
            print(html)
        except Exception as e:
            debug(f"Error processing file {json_file}: {e}")
            sys.exit(1)
    else:
        debug("Usage: python3 owasp_dependency_check_processor.py <json_file>")
        sys.exit(1)
