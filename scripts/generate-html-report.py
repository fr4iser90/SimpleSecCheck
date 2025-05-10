#!/usr/bin/env python3
import os
import json
import datetime
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

RESULTS_DIR = os.environ.get('RESULTS_DIR', '/seculite/results')
OUTPUT_FILE = '/seculite/results/security-summary.html'

def debug(msg):
    print(f"[generate-html-report] {msg}", file=sys.stderr)

def read_json(path):
    if not Path(path).exists():
        debug(f"Missing JSON file: {path}")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        debug(f"Error reading JSON file {path}: {e}")
        return None

def zap_summary(zap_html_path, zap_xml_path):
    # Try XML first
    if zap_xml_path and Path(zap_xml_path).exists():
        try:
            tree = ET.parse(zap_xml_path)
            root = tree.getroot()
            alerts = root.findall('.//alertitem')
            summary = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
            for alert in alerts:
                riskdesc = alert.findtext('riskdesc', 'Unknown')
                if riskdesc.startswith('High'):
                    summary["High"] += 1
                elif riskdesc.startswith('Medium'):
                    summary["Medium"] += 1
                elif riskdesc.startswith('Low'):
                    summary["Low"] += 1
                elif riskdesc.startswith('Informational'):
                    summary["Informational"] += 1
            return summary
        except Exception as e:
            debug(f"Error parsing ZAP XML: {e}")
    # Fallback: Try HTML
    if zap_html_path and Path(zap_html_path).exists():
        try:
            with open(zap_html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                summary_table = soup.find('table', class_='summary')
                summary = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
                if summary_table:
                    rows = summary_table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            risk = cols[0].get_text(strip=True)
                            count = cols[1].get_text(strip=True)
                            if risk in summary:
                                try:
                                    summary[risk] = int(count)
                                except Exception:
                                    pass
                return summary
        except Exception as e:
            debug(f"Error parsing ZAP HTML: {e}")
    # Fallback: all zeros
    return {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}

def semgrep_summary(semgrep_json):
    findings = []
    if semgrep_json and 'results' in semgrep_json:
        for r in semgrep_json['results']:
            findings.append({
                'check_id': r.get('check_id', ''),
                'path': r.get('path', ''),
                'start': r.get('start', {}).get('line', ''),
                'message': r.get('extra', {}).get('message', ''),
                'severity': r.get('extra', {}).get('severity', '')
            })
    else:
        debug("No Semgrep results found in JSON.")
    return findings

def trivy_summary(trivy_json):
    vulns = []
    if trivy_json and 'Results' in trivy_json:
        for result in trivy_json['Results']:
            for v in result.get('Vulnerabilities', []):
                vulns.append({
                    'PkgName': v.get('PkgName', ''),
                    'Severity': v.get('Severity', ''),
                    'VulnerabilityID': v.get('VulnerabilityID', ''),
                    'Title': v.get('Title', ''),
                    'Description': v.get('Description', '')
                })
    else:
        debug("No Trivy results found in JSON.")
    return vulns

def html_header(title):
    return f'''<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>{title}</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<style>\n:root {{\n  --bg-light: #f8f9fa;\n  --bg-dark: #181a1b;\n  --text-light: #181a1b;\n  --text-dark: #f8f9fa;\n  --accent: #007bff;\n  --table-bg: #fff;\n  --table-bg-dark: #23272b;\n  --table-border: #dee2e6;\n  --table-border-dark: #343a40;\n}}\nbody {{\n  background: var(--bg-light);\n  color: var(--text-light);\n  font-family: 'Segoe UI', Arial, sans-serif;\n  margin: 0; padding: 0;\n  transition: background 0.2s, color 0.2s;\n}}\nbody.darkmode {{\n  background: var(--bg-dark);\n  color: var(--text-dark);\n}}\n.header {{\n  display: flex; justify-content: space-between; align-items: center;\n  padding: 1.2em 2em 0.5em 2em;\n  background: var(--bg-light);\n  border-bottom: 1px solid var(--table-border);\n}}\nbody.darkmode .header {{\n  background: var(--bg-dark);\n  border-bottom: 1px solid var(--table-border-dark);\n}}\n.toggle-btn {{\n  background: var(--accent);\n  color: #fff;\n  border: none;\n  border-radius: 1.5em;\n  padding: 0.5em 1.2em;\n  font-size: 1em;\n  cursor: pointer;\n  transition: background 0.2s;\n}}\n.toggle-btn:hover {{\n  background: #0056b3;\n}}\nh1, h2, h3 {{ margin: 0; font-size: 2em; }}\nh2 {{ margin-top: 2em; }}\ntable {{\n  border-collapse: collapse;\n  width: 100%;\n  margin: 1em 0;\n  background: var(--table-bg);\n  color: inherit;\n}}\nbody.darkmode table {{\n  background: var(--table-bg-dark);\n}}\nth, td {{\n  border: 1px solid var(--table-border);\n  padding: 0.5em 1em;\n  text-align: left;\n}}\nbody.darkmode th, body.darkmode td {{\n  border: 1px solid var(--table-border-dark);\n}}\na {{\n  color: var(--accent);\n  text-decoration: none;\n}}\na:hover {{\n  text-decoration: underline;\n}}\n.summary-box {{\n  background: #e9ecef;\n  border-radius: 0.5em;\n  padding: 1em;\n  margin: 1.5em 0;\n}}\nbody.darkmode .summary-box {{\n  background: #23272b;\n}}\n</style>\n<script>\nfunction toggleDarkMode() {{\n  document.body.classList.toggle('darkmode');\n  localStorage.setItem('seculite-darkmode', document.body.classList.contains('darkmode'));\n}}\nwindow.onload = function() {{\n  if (localStorage.getItem('seculite-darkmode') === 'true') {{\n    document.body.classList.add('darkmode');\n  }}\n}};\n</script>\n</head>\n<body>\n<div class="header">\n  <h1>SecuLite Security Scan Summary</h1>\n  <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n</div>\n<div class="summary-box">'''

def html_footer():
    return '</div>\n</body></html>'

def main():
    debug(f"Starting HTML report generation. Output: {OUTPUT_FILE}")
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    target = os.environ.get('ZAP_TARGET', 'Unknown')
    zap_html_path = os.path.join(RESULTS_DIR, 'zap-report.xml.html')
    zap_xml_path = os.path.join(RESULTS_DIR, 'zap-report.xml')
    semgrep_json_path = os.path.join(RESULTS_DIR, 'semgrep.json')
    trivy_json_path = os.path.join(RESULTS_DIR, 'trivy.json')

    semgrep_json = read_json(semgrep_json_path)
    trivy_json = read_json(trivy_json_path)
    zap_alerts = zap_summary(zap_html_path, zap_xml_path)
    semgrep_findings = semgrep_summary(semgrep_json)
    trivy_vulns = trivy_summary(trivy_json)

    try:
        with open(OUTPUT_FILE, 'w') as f:
            f.write(html_header('SecuLite Security Scan Summary'))
            f.write(f'<h1>SecuLite Security Scan Summary</h1>\n')
            f.write(f'<p><b>Scan Date:</b> {now}<br>')
            f.write(f'<b>Target:</b> {target}</p>\n')
            f.write('<h2>Overall Summary</h2>\n')
            f.write('<ul>')
            f.write(f'<li>ZAP Alerts: {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Informational</li>')
            f.write(f'<li>Semgrep Findings: {len(semgrep_findings)}</li>')
            f.write(f'<li>Trivy Vulnerabilities: {len(trivy_vulns)}</li>')
            f.write('</ul>')
            f.write('<h2>Links to Raw Reports</h2>\n<ul>')
            for name in ['zap-report.html', 'zap-report.xml', 'semgrep.json', 'trivy.json', 'semgrep.txt', 'trivy.txt']:
                path = os.path.join(RESULTS_DIR, name)
                if Path(path).exists():
                    f.write(f'<li><a href="{name}">{name}</a></li>')
            f.write('</ul>')

            # ZAP Section
            f.write('<h2>ZAP Web Vulnerability Scan</h2>')
            if zap_alerts:
                f.write('<table><tr><th>Risk Level</th><th>Number of Alerts</th></tr>')
                for risk, count in zap_alerts.items():
                    f.write(f'<tr><td>{risk}</td><td>{count}</td></tr>')
                f.write('</table>')
            else:
                f.write('<p><b>Scan completed. No web vulnerabilities found.</b></p>')
            if Path(zap_html_path).exists():
                f.write(f'<p>See full ZAP report: <a href="zap-report.html">zap-report.html</a></p>')

            # Semgrep Section
            f.write('<h2>Semgrep Static Code Analysis</h2>')
            if semgrep_findings:
                f.write('<table><tr><th>Rule</th><th>File</th><th>Line</th><th>Message</th><th>Severity</th></tr>')
                for finding in semgrep_findings:
                    sev = finding['severity'].upper()
                    f.write(f'<tr><td>{finding["check_id"]}</td><td>{finding["path"]}</td><td>{finding["start"]}</td><td>{finding["message"]}</td><td class="severity-{sev}">{sev}</td></tr>')
                f.write('</table>')
            else:
                f.write('<p><b>Scan completed. No code vulnerabilities found.</b></p>')

            # Trivy Section
            f.write('<h2>Trivy Dependency & Container Scan</h2>')
            if trivy_vulns:
                f.write('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
                for v in trivy_vulns:
                    sev = v['Severity'].upper()
                    f.write(f'<tr><td>{v["PkgName"]}</td><td class="severity-{sev}">{sev}</td><td>{v["VulnerabilityID"]}</td><td>{v["Title"]}</td></tr>')
                f.write('</table>')
            else:
                f.write('<p><b>Scan completed. No vulnerabilities found in dependencies or containers.</b></p>')

            f.write(html_footer())
        debug(f"HTML report successfully written to {OUTPUT_FILE}")
    except Exception as e:
        debug(f"Failed to write HTML report: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 