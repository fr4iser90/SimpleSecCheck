#!/usr/bin/env python3
import os
import json
import datetime
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

RESULTS_DIR = os.environ.get('RESULTS_DIR', '/seculite/results')
OUTPUT_FILE = '/seculite/results/security-summary.html'

# Dynamische LLM-Client-Auswahl
llm_provider = os.environ.get('LLM_PROVIDER', 'openai').lower()
llm_config = {
    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
    'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
    'OPENAI_ENDPOINT': os.environ.get('OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions'),
    'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY', ''),
    'GEMINI_MODEL': os.environ.get('GEMINI_MODEL', 'gemini-pro'),
    'GEMINI_ENDPOINT': os.environ.get('GEMINI_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models'),
    'HF_API_KEY': os.environ.get('HF_API_KEY', ''),
    'HF_MODEL': os.environ.get('HF_MODEL', 'bigcode/starcoder2-15b'),
    'HF_ENDPOINT': os.environ.get('HF_ENDPOINT', 'https://api-inference.huggingface.co/models'),
    'GROQ_API_KEY': os.environ.get('GROQ_API_KEY', ''),
    'GROQ_MODEL': os.environ.get('GROQ_MODEL', 'llama3-70b-8192'),
    'GROQ_ENDPOINT': os.environ.get('GROQ_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
    'MISTRAL_API_KEY': os.environ.get('MISTRAL_API_KEY', ''),
    'MISTRAL_MODEL': os.environ.get('MISTRAL_MODEL', 'mistral-medium'),
    'MISTRAL_ENDPOINT': os.environ.get('MISTRAL_ENDPOINT', 'https://api.mistral.ai/v1/chat/completions'),
    'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
    'ANTHROPIC_MODEL': os.environ.get('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
    'ANTHROPIC_ENDPOINT': os.environ.get('ANTHROPIC_ENDPOINT', 'https://api.anthropic.com/v1/messages'),
}

if llm_provider == 'openai':
    from scripts.llm.llm_client_openai import OpenAILLMClient
    llm_client = OpenAILLMClient(llm_config)
elif llm_provider == 'gemini':
    from scripts.llm.llm_client_gemini import GeminiLLMClient
    llm_client = GeminiLLMClient(llm_config)
elif llm_provider == 'huggingface':
    from scripts.llm.llm_client_huggingface import HuggingFaceLLMClient
    llm_client = HuggingFaceLLMClient(llm_config)
elif llm_provider == 'groq':
    from scripts.llm.llm_client_groq import GroqLLMClient
    llm_client = GroqLLMClient(llm_config)
elif llm_provider == 'mistral':
    from scripts.llm.llm_client_mistral import MistralLLMClient
    llm_client = MistralLLMClient(llm_config)
elif llm_provider == 'anthropic':
    from scripts.llm.llm_client_anthropic import AnthropicLLMClient
    llm_client = AnthropicLLMClient(llm_config)
else:
    from scripts.llm.llm_client_openai import OpenAILLMClient
    llm_client = OpenAILLMClient(llm_config)

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
            finding = {
                'check_id': r.get('check_id', ''),
                'path': r.get('path', ''),
                'start': r.get('start', {}).get('line', ''),
                'message': r.get('extra', {}).get('message', ''),
                'severity': r.get('extra', {}).get('severity', '')
            }
            # LLM integration: generate prompt and get AI explanation
            prompt = f"Explain and suggest a fix for this finding: {finding['message']} in {finding['path']} at line {finding['start']}"
            finding['ai_explanation'] = llm_client.query(prompt)
            findings.append(finding)
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
  localStorage.setItem('seculite-darkmode', document.body.classList.contains('darkmode'));
}}
window.onload = function() {{
  if (localStorage.getItem('seculite-darkmode') === 'true') {{
    document.body.classList.add('darkmode');
  }}
}};\n</script>\n<script src="webui.js"></script>\n</head>\n<body>\n<div class="header">\n  <h1>SecuLite Security Scan Summary</h1>\n  <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n</div>\n<div class="summary-box">'''

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
            f.write(f'<p><b>Scan Date:</b> {now}<br>')
            f.write(f'<b>Target:</b> {target}</p>\n')
            # WebUI Controls Block
            f.write('''\n<!-- WebUI Controls -->\n<div style="margin: 1em 0;">\n  <button id="scan-btn">Jetzt neuen Scan starten</button>\n  <button id="refresh-status-btn">Status aktualisieren</button>\n  <span id="scan-status" style="margin-left:1em; color: #007bff;">Status wird geladen...</span>\n</div>\n<!-- Hinweis: Scan-Status und Trigger laufen über Port 9100 (Watchdog) -->\n''')

            # --- Visual summary with icons/colors for each tool ---
            # ZAP
            zap_icon = '✅' if sum(zap_alerts.values()) == 0 else ''
            if zap_alerts['High'] > 0:
                zap_icon = '🚨'
            elif zap_alerts['Medium'] > 0:
                zap_icon = '⚠️'
            elif zap_alerts['Low'] > 0 or zap_alerts['Informational'] > 0:
                zap_icon = 'ℹ️'
            f.write(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if zap_alerts["High"]>0 else ("MEDIUM" if zap_alerts["Medium"]>0 else ("LOW" if zap_alerts["Low"]>0 else ("INFO" if zap_alerts["Informational"]>0 else "PASSED")))}">{zap_icon}</span> <b>ZAP:</b> {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Info</div>')
            # Semgrep
            if len(semgrep_findings) == 0:
                f.write('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Semgrep:</b> No findings</div>')
            else:
                f.write(f'<div class="tool-summary"><span class="icon sev-HIGH">🚨</span> <b>Semgrep:</b> {len(semgrep_findings)} findings</div>')
            # Trivy
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
            f.write(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if trivy_counts["CRITICAL"]>0 else ("HIGH" if trivy_counts["HIGH"]>0 else ("MEDIUM" if trivy_counts["MEDIUM"]>0 else ("LOW" if trivy_counts["LOW"]>0 else ("INFO" if trivy_counts["INFO"]>0 else "PASSED"))))}">{trivy_icon}</span> <b>Trivy:</b> {trivy_counts["CRITICAL"]} Critical, {trivy_counts["HIGH"]} High, {trivy_counts["MEDIUM"]} Medium, {trivy_counts["LOW"]} Low, {trivy_counts["INFO"]} Info</div>')

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
                    icon = ''
                    sev_class = risk.upper()
                    if risk == 'High': icon = '🚨'
                    elif risk == 'Medium': icon = '⚠️'
                    elif risk == 'Low': icon = 'ℹ️'
                    elif risk == 'Informational': icon = 'ℹ️'
                    f.write(f'<tr class="row-{sev_class}"><td class="severity-{sev_class}">{icon} {risk}</td><td>{count}</td></tr>')
                f.write('</table>')
                if sum(zap_alerts.values()) == 0:
                    f.write('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>')
            else:
                f.write('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>')
            if Path(zap_html_path).exists():
                f.write(f'<p>See full ZAP report: <a href="zap-report.xml.html">zap-report.xml.html</a></p>')
            elif Path(os.path.join(RESULTS_DIR, "zap-report.html")).exists():
                f.write(f'<p>See full ZAP report: <a href="zap-report.html">zap-report.html</a></p>')

            # Semgrep Section
            f.write('<h2>Semgrep Static Code Analysis</h2>')
            if semgrep_findings:
                f.write('<table><tr><th>Rule</th><th>File</th><th>Line</th><th>Message</th><th>Severity</th><th>AI Explanation</th></tr>')
                for finding in semgrep_findings:
                    sev = finding['severity'].upper()
                    icon = ''
                    if sev == 'CRITICAL': icon = '🚨'
                    elif sev == 'HIGH': icon = '🚨'
                    elif sev == 'MEDIUM': icon = '⚠️'
                    elif sev == 'LOW': icon = 'ℹ️'
                    elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
                    ai_exp = finding.get('ai_explanation', '')
                    f.write(f'<tr class="row-{sev}"><td>{finding["check_id"]}</td><td>{finding["path"]}</td><td>{finding["start"]}</td><td>{finding["message"]}</td><td class="severity-{sev}">{icon} {sev}</td><td>{ai_exp}</td></tr>')
                f.write('</table>')
            else:
                f.write('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code vulnerabilities found.</div>')

            # Trivy Section
            f.write('<h2>Trivy Dependency & Container Scan</h2>')
            if trivy_vulns:
                f.write('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
                for v in trivy_vulns:
                    sev = v['Severity'].upper()
                    icon = ''
                    if sev == 'CRITICAL': icon = '🚨'
                    elif sev == 'HIGH': icon = '🚨'
                    elif sev == 'MEDIUM': icon = '⚠️'
                    elif sev == 'LOW': icon = 'ℹ️'
                    elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
                    f.write(f'<tr class="row-{sev}"><td>{v["PkgName"]}</td><td class="severity-{sev}">{icon} {sev}</td><td>{v["VulnerabilityID"]}</td><td>{v["Title"]}</td></tr>')
                f.write('</table>')
            else:
                f.write('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in dependencies or containers.</div>')

            f.write(html_footer())
        debug(f"HTML report successfully written to {OUTPUT_FILE}")
    except Exception as e:
        debug(f"Failed to write HTML report: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 