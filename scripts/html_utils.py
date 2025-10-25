#!/usr/bin/env python3

def html_header(title):
    # Content of html_header function (lines 162-297 from the original generate-html-report.py)
    return f'''<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>{title}</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<style>\n:root {{
  --bg-light: #f8f9fa;
  --bg-dark: #181a1b;
  --text-light: #181a1b;
  --text-dark: #f8f9fa;
  --accent: #007bff;
  --table-bg: #fff;
  --table-bg-dark: #23272b;
  --table-border: #dee2e6;
  --table-border-dark: #343a40;
  --sev-critical: #b30000;
  --sev-high: #e67300;
  --sev-medium: #e6b800;
  --sev-low: #007399;
  --sev-info: #666;
  --sev-passed: #28a745;
  --sev-bg-critical: #ffeaea;
  --sev-bg-high: #fff4e5;
  --sev-bg-medium: #fffbe5;
  --sev-bg-low: #e5f6fa;
  --sev-bg-info: #f0f0f0;
  --sev-bg-passed: #e6f9ed;
}}
body {{
  background: var(--bg-light);
  color: var(--text-light);
  font-family: 'Segoe UI', Arial, sans-serif;
  margin: 0; padding: 0;
  transition: background 0.2s, color 0.2s;
}}
body.darkmode {{
  background: var(--bg-dark);
  color: var(--text-dark);
}}
.header {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.2em 2em 0.5em 2em;
  background: var(--bg-light);
  border-bottom: 1px solid var(--table-border);
}}
body.darkmode .header {{
  background: var(--bg-dark);
  border-bottom: 1px solid var(--table-border-dark);
}}
.toggle-btn {{
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 1.5em;
  padding: 0.5em 1.2em;
  font-size: 1em;
  cursor: pointer;
  transition: background 0.2s;
}}
.toggle-btn:hover {{
  background: #0056b3;
}}
h1, h2, h3 {{ margin: 0; font-size: 2em; }}
h2 {{ margin-top: 2em; }}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  background: var(--table-bg);
  color: inherit;
}}
body.darkmode table {{
  background: var(--table-bg-dark);
}}
th, td {{
  border: 1px solid var(--table-border);
  padding: 0.5em 1em;
  text-align: left;
}}
body.darkmode th, body.darkmode td {{
  border: 1px solid var(--table-border-dark);
}}
a {{
  color: var(--accent);
  text-decoration: none;
}}
a:hover {{
  text-decoration: underline;
}}
.summary-box {{
  background: #e9ecef;
  border-radius: 0.5em;
  padding: 1em;
  margin: 1.5em 0;
}}
body.darkmode .summary-box {{
  background: #23272b;
}}
.severity-CRITICAL, .sev-CRITICAL {{ color: var(--sev-critical); font-weight: bold; }}
.severity-HIGH, .sev-HIGH {{ color: var(--sev-high); font-weight: bold; }}
.severity-MEDIUM, .sev-MEDIUM {{ color: var(--sev-medium); font-weight: bold; }}
.severity-LOW, .sev-LOW {{ color: var(--sev-low); }}
.severity-INFO, .severity-INFORMATIONAL, .sev-INFO, .sev-INFORMATIONAL {{ color: var(--sev-info); }}
.severity-PASSED, .sev-PASSED {{ color: var(--sev-passed); font-weight: bold; }}
.row-CRITICAL {{ background: var(--sev-bg-critical); }}
.row-HIGH {{ background: var(--sev-bg-high); }}
.row-MEDIUM {{ background: var(--sev-bg-medium); }}
.row-LOW {{ background: var(--sev-bg-low); }}
.row-INFO, .row-INFORMATIONAL {{ background: var(--sev-bg-info); }}
.row-PASSED {{ background: var(--sev-bg-passed); }}
.all-clear {{ background: var(--sev-bg-passed); color: var(--sev-passed); border-radius: 0.5em; padding: 1em; margin: 1em 0; font-weight: bold; display: flex; align-items: center; gap: 0.7em; font-size: 1.2em; }}
.icon {{ font-size: 1.2em; vertical-align: middle; margin-right: 0.3em; }}
/* --- Fix contrast in dark mode --- */
body.darkmode .row-CRITICAL td, body.darkmode .row-CRITICAL th {{ color: #fff !important; background: #a94442 !important; }}
body.darkmode .row-HIGH td, body.darkmode .row-HIGH th {{ color: #fff !important; background: #e67c00 !important; }}
body.darkmode .row-MEDIUM td, body.darkmode .row-MEDIUM th {{ color: #222 !important; background: #ffe066 !important; }}
body.darkmode .row-LOW td, body.darkmode .row-LOW th {{ color: #003366 !important; background: #b3e6f7 !important; }}
body.darkmode .row-INFO td, body.darkmode .row-INFO th, body.darkmode .row-INFORMATIONAL td, body.darkmode .row-INFORMATIONAL th {{ color: #222 !important; background: #bfc9d1 !important; }}
body.darkmode .row-PASSED td, body.darkmode .row-PASSED th {{ color: #155724 !important; background: #b7f7d8 !important; }}
</style>\n<script>\nfunction toggleDarkMode() {{
  document.body.classList.toggle('darkmode');
  localStorage.setItem('SimpleSecCheck-darkmode', document.body.classList.contains('darkmode'));
}}
window.onload = function() {{
  if (localStorage.getItem('SimpleSecCheck-darkmode') === 'true') {{
    document.body.classList.add('darkmode');
  }}
}};
</script>\n<script src="webui.js"></script>\n</head>\n<body>\n<div class="header">\n  <h1>SimpleSecCheck Security Scan Summary</h1>\n  <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n</div>\n<div class="summary-box">'''

def html_footer():
    # Content of html_footer function (lines 299-300 from the original generate-html-report.py)
    return '</div>\n</body></html>'

def generate_visual_summary_section(zap_alerts, semgrep_findings, trivy_vulns):
    html_parts = []
    # ZAP Visual Summary
    zap_icon = '✅' if sum(zap_alerts.values()) == 0 else ''
    if zap_alerts['High'] > 0:
        zap_icon = '🚨'
    elif zap_alerts['Medium'] > 0:
        zap_icon = '⚠️'
    elif zap_alerts['Low'] > 0 or zap_alerts['Informational'] > 0:
        zap_icon = 'ℹ️'
    html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if zap_alerts["High"]>0 else ("MEDIUM" if zap_alerts["Medium"]>0 else ("LOW" if zap_alerts["Low"]>0 else ("INFO" if zap_alerts["Informational"]>0 else "PASSED")))}">{zap_icon}</span> <b>ZAP:</b> {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Info</div>')
    
    # Semgrep Visual Summary
    if len(semgrep_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Semgrep:</b> No findings</div>')
    else:
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-HIGH">🚨</span> <b>Semgrep:</b> {len(semgrep_findings)} findings</div>')
        
    # Trivy Visual Summary
    trivy_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for v in trivy_vulns:
        sev = v['Severity'].upper()
        if sev in trivy_counts:
            trivy_counts[sev] += 1
    trivy_icon = '✅' if sum(trivy_counts.values()) == 0 else ''
    if trivy_counts['CRITICAL'] > 0:
        trivy_icon = '🚨'
    elif trivy_counts['HIGH'] > 0:
        trivy_icon = '🚨'
    elif trivy_counts['MEDIUM'] > 0:
        trivy_icon = '⚠️'
    elif trivy_counts['LOW'] > 0 or trivy_counts['INFO'] > 0:
        trivy_icon = 'ℹ️'
    html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if trivy_counts["CRITICAL"]>0 else ("HIGH" if trivy_counts["HIGH"]>0 else ("MEDIUM" if trivy_counts["MEDIUM"]>0 else ("LOW" if trivy_counts["LOW"]>0 else ("INFO" if trivy_counts["INFO"]>0 else "PASSED"))))}">{trivy_icon}</span> <b>Trivy:</b> {trivy_counts["CRITICAL"]} Critical, {trivy_counts["HIGH"]} High, {trivy_counts["MEDIUM"]} Medium, {trivy_counts["LOW"]} Low, {trivy_counts["INFO"]} Info</div>')
    return "".join(html_parts)

def generate_overall_summary_and_links_section(zap_alerts, semgrep_findings, trivy_vulns, RESULTS_DIR, Path_module, os_module):
    html_parts = []
    html_parts.append('<h2>Overall Summary</h2>\n')
    html_parts.append('<ul>')
    html_parts.append(f'<li>ZAP Alerts: {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Informational</li>')
    html_parts.append(f'<li>Semgrep Findings: {len(semgrep_findings)}</li>')
    html_parts.append(f'<li>Trivy Vulnerabilities: {len(trivy_vulns)}</li>')
    html_parts.append('</ul>')
    html_parts.append('<h2>Links to Raw Reports</h2>\n<ul>')
    for name in ['zap-report.html', 'zap-report.xml', 'semgrep.json', 'trivy.json', 'semgrep.txt', 'trivy.txt']:
        # Path_module and os_module are used here for consistency, though os_module.path.join is the key part
        path = os_module.path.join(RESULTS_DIR, name)
        if Path_module(path).exists():
            html_parts.append(f'<li><a href="{name}">{name}</a></li>')
    html_parts.append('</ul>')
    return "".join(html_parts) 