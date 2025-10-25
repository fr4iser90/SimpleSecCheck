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
from scripts.html_utils import html_header, html_footer, generate_visual_summary_section, generate_overall_summary_and_links_section
from scripts.zap_processor import zap_summary, generate_zap_html_section
from scripts.zap_xml_parser import parse_zap_xml, generate_html_report
from scripts.semgrep_processor import semgrep_summary, generate_semgrep_html_section
from scripts.trivy_processor import trivy_summary, generate_trivy_html_section
from scripts.llm_connector import llm_client

RESULTS_DIR = os.environ.get('RESULTS_DIR', '/SimpleSecCheck/results')
OUTPUT_FILE = '/SimpleSecCheck/results/security-summary.html'

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

def main():
    debug(f"Starting HTML report generation. Output: {OUTPUT_FILE}")
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    target = os.environ.get('ZAP_TARGET', os.environ.get('TARGET_URL', 'Unknown'))
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
            f.write(html_header('SimpleSecCheck Security Scan Summary'))
            f.write(f'<p><b>Scan Date:</b> {now}<br>')
            f.write(f'<b>Target:</b> {target}</p>\n')
            # WebUI Controls Block
            f.write('''\n<!-- WebUI Controls -->\n<div style="margin: 1em 0;">\n  <button id="scan-btn">Jetzt neuen Scan starten</button>\n  <button id="refresh-status-btn">Status aktualisieren</button>\n  <span id="scan-status" style="margin-left:1em; color: #007bff;">Status wird geladen...</span>\n</div>\n<!-- Hinweis: Scan-Status und Trigger laufen über Port 9100 (Watchdog) -->\n''')

            # --- Visual summary with icons/colors for each tool ---
            f.write(generate_visual_summary_section(zap_alerts.get('summary', zap_alerts), semgrep_findings, trivy_vulns))

            # --- Overall Summary and Links ---
            f.write(generate_overall_summary_and_links_section(zap_alerts.get('summary', zap_alerts), semgrep_findings, trivy_vulns, RESULTS_DIR, Path, os))

            # ZAP Section - pass the full zap_alerts data structure
            f.write(generate_zap_html_section(zap_alerts, zap_html_path, Path, os))

            # Semgrep Section
            f.write(generate_semgrep_html_section(semgrep_findings))

            # Trivy Section
            f.write(generate_trivy_html_section(trivy_vulns))

            f.write(html_footer())
        debug(f"HTML report successfully written to {OUTPUT_FILE}")
    except Exception as e:
        debug(f"Failed to write HTML report: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 