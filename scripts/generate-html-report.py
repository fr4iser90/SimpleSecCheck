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
from scripts.codeql_processor import codeql_summary, generate_codeql_html_section
from scripts.nuclei_processor import nuclei_summary, generate_nuclei_html_section
from scripts.owasp_dependency_check_processor import owasp_dependency_check_summary, generate_owasp_dependency_check_html_section
from scripts.safety_processor import safety_summary, generate_safety_html_section
from scripts.snyk_processor import snyk_summary, generate_snyk_html_section
from scripts.sonarqube_processor import sonarqube_summary, generate_sonarqube_html_section
from scripts.terraform_security_processor import checkov_summary as terraform_checkov_summary, generate_checkov_html_section as generate_terraform_checkov_html_section
from scripts.checkov_processor import checkov_summary, generate_checkov_html_section
from scripts.trufflehog_processor import trufflehog_summary, generate_trufflehog_html_section
from scripts.gitleaks_processor import gitleaks_summary, generate_gitleaks_html_section
from scripts.detect_secrets_processor import detect_secrets_summary, generate_detect_secrets_html_section
from scripts.npm_audit_processor import npm_audit_summary, generate_npm_audit_html_section
from scripts.wapiti_processor import wapiti_summary, generate_wapiti_html_section
from scripts.nikto_processor import nikto_summary, generate_nikto_html_section
from scripts.kube_hunter_processor import kube_hunter_summary, generate_kube_hunter_html_section
from scripts.kube_bench_processor import kube_bench_summary, generate_kube_bench_html_section
from scripts.docker_bench_processor import docker_bench_summary, generate_docker_bench_html_section
from scripts.eslint_processor import eslint_summary, generate_eslint_html_section
from scripts.clair_processor import clair_summary, generate_clair_html_section
from scripts.anchore_processor import anchore_summary, generate_anchore_html_section
from scripts.burp_processor import burp_summary, generate_burp_html_section
from scripts.brakeman_processor import brakeman_summary, generate_brakeman_html_section
from scripts.bandit_processor import bandit_summary, generate_bandit_html_section

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
    scan_type = os.environ.get('SCAN_TYPE', 'code')
    zap_html_path = os.path.join(RESULTS_DIR, 'zap-report.xml.html')
    zap_xml_path = os.path.join(RESULTS_DIR, 'zap-report.xml')
    semgrep_json_path = os.path.join(RESULTS_DIR, 'semgrep.json')
    trivy_json_path = os.path.join(RESULTS_DIR, 'trivy.json')
    codeql_json_path = os.path.join(RESULTS_DIR, 'codeql.json')
    nuclei_json_path = os.path.join(RESULTS_DIR, 'nuclei.json')
    owasp_dc_json_path = os.path.join(RESULTS_DIR, 'owasp-dependency-check.json')
    safety_json_path = os.path.join(RESULTS_DIR, 'safety.json')
    snyk_json_path = os.path.join(RESULTS_DIR, 'snyk.json')
    sonarqube_json_path = os.path.join(RESULTS_DIR, 'sonarqube.json')
    checkov_json_path = os.path.join(RESULTS_DIR, 'checkov.json')
    checkov_comprehensive_json_path = os.path.join(RESULTS_DIR, 'checkov-comprehensive.json')
    trufflehog_json_path = os.path.join(RESULTS_DIR, 'trufflehog.json')
    gitleaks_json_path = os.path.join(RESULTS_DIR, 'gitleaks.json')
    detect_secrets_json_path = os.path.join(RESULTS_DIR, 'detect-secrets.json')
    npm_audit_json_path = os.path.join(RESULTS_DIR, 'npm-audit.json')
    wapiti_json_path = os.path.join(RESULTS_DIR, 'wapiti.json')
    nikto_json_path = os.path.join(RESULTS_DIR, 'nikto.json')
    burp_json_path = os.path.join(RESULTS_DIR, 'burp.json')
    kube_hunter_json_path = os.path.join(RESULTS_DIR, 'kube-hunter.json')
    kube_bench_json_path = os.path.join(RESULTS_DIR, 'kube-bench.json')
    docker_bench_json_path = os.path.join(RESULTS_DIR, 'docker-bench.json')
    eslint_json_path = os.path.join(RESULTS_DIR, 'eslint.json')
    clair_json_path = os.path.join(RESULTS_DIR, 'clair.json')
    anchore_json_path = os.path.join(RESULTS_DIR, 'anchore.json')
    brakeman_json_path = os.path.join(RESULTS_DIR, 'brakeman.json')
    bandit_json_path = os.path.join(RESULTS_DIR, 'bandit.json')

    semgrep_json = read_json(semgrep_json_path)
    trivy_json = read_json(trivy_json_path)
    codeql_json = read_json(codeql_json_path)
    nuclei_json = read_json(nuclei_json_path)
    owasp_dc_json = read_json(owasp_dc_json_path)
    safety_json = read_json(safety_json_path)
    snyk_json = read_json(snyk_json_path)
    sonarqube_json = read_json(sonarqube_json_path)
    checkov_json = read_json(checkov_json_path)
    checkov_comprehensive_json = read_json(checkov_comprehensive_json_path)
    trufflehog_json = read_json(trufflehog_json_path)
    gitleaks_json = read_json(gitleaks_json_path)
    detect_secrets_json = read_json(detect_secrets_json_path)
    npm_audit_json = read_json(npm_audit_json_path)
    wapiti_json = read_json(wapiti_json_path)
    nikto_json = read_json(nikto_json_path)
    burp_json = read_json(burp_json_path)
    kube_hunter_json = read_json(kube_hunter_json_path)
    kube_bench_json = read_json(kube_bench_json_path)
    docker_bench_json = read_json(docker_bench_json_path)
    eslint_json = read_json(eslint_json_path)
    clair_json = read_json(clair_json_path)
    anchore_json = read_json(anchore_json_path)
    brakeman_json = read_json(brakeman_json_path)
    zap_alerts = zap_summary(zap_html_path, zap_xml_path)
    semgrep_findings = semgrep_summary(semgrep_json)
    trivy_vulns = trivy_summary(trivy_json)
    codeql_findings = codeql_summary(codeql_json)
    nuclei_findings = nuclei_summary(nuclei_json)
    owasp_dc_vulns = owasp_dependency_check_summary(owasp_dc_json)
    safety_findings = safety_summary(safety_json)
    snyk_findings = snyk_summary(snyk_json)
    sonarqube_findings = sonarqube_summary(sonarqube_json)
    checkov_findings = terraform_checkov_summary(checkov_json)
    checkov_comprehensive_findings = checkov_summary(checkov_comprehensive_json)
    trufflehog_findings = trufflehog_summary(trufflehog_json)
    gitleaks_findings = gitleaks_summary(gitleaks_json)
    detect_secrets_findings = detect_secrets_summary(detect_secrets_json)
    npm_audit_findings = npm_audit_summary(npm_audit_json)
    wapiti_findings = wapiti_summary(wapiti_json)
    nikto_findings = nikto_summary(nikto_json)
    burp_findings = burp_summary(burp_json)
    kube_hunter_findings = kube_hunter_summary(kube_hunter_json)
    kube_bench_findings = kube_bench_summary(kube_bench_json)
    docker_bench_findings = docker_bench_summary(docker_bench_json)
    eslint_findings = eslint_summary(eslint_json)
    clair_vulns = clair_summary(clair_json)
    anchore_vulns = anchore_summary(anchore_json)
    brakeman_findings = brakeman_summary(brakeman_json)
    bandit_findings = bandit_summary(read_json(bandit_json_path))

    try:
        with open(OUTPUT_FILE, 'w') as f:
            f.write(html_header('SimpleSecCheck Security Scan Summary'))
            f.write(f'<p><b>Scan Date:</b> {now}<br>')
            f.write(f'<b>Target:</b> {target}</p>\n')
            # WebUI Controls Block
            f.write('''\n<!-- WebUI Controls -->\n<div style="margin: 1em 0;">\n  <button id="scan-btn">Jetzt neuen Scan starten</button>\n  <button id="refresh-status-btn">Status aktualisieren</button>\n  <span id="scan-status" style="margin-left:1em; color: #007bff;">Status wird geladen...</span>\n</div>\n<!-- Hinweis: Scan-Status und Trigger laufen über Port 9100 (Watchdog) -->\n''')

            # --- Visual summary with icons/colors for each tool ---
            f.write(generate_visual_summary_section(zap_alerts.get('summary', zap_alerts), semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_comprehensive_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_vulns, anchore_vulns, brakeman_findings, bandit_findings))

            # ZAP Section (only if findings exist)
            if sum(zap_alerts.get('summary', zap_alerts).values()) > 0:
                f.write(generate_zap_html_section(zap_alerts, zap_html_path, Path, os))

            # Semgrep Section (only if findings exist)
            if len(semgrep_findings) > 0:
                f.write(generate_semgrep_html_section(semgrep_findings))

            # Trivy Section (only if findings exist)
            if len(trivy_vulns) > 0:
                f.write(generate_trivy_html_section(trivy_vulns))

            # CodeQL Section (only if findings exist)
            if len(codeql_findings) > 0:
                f.write(generate_codeql_html_section(codeql_findings))

            # Nuclei Section (only if findings exist)
            if len(nuclei_findings) > 0:
                f.write(generate_nuclei_html_section(nuclei_findings))

            # OWASP Dependency Check Section (only if findings exist)
            if len(owasp_dc_vulns) > 0:
                f.write(generate_owasp_dependency_check_html_section(owasp_dc_vulns))

            # Safety Section (only if findings exist)
            if len(safety_findings) > 0:
                f.write(generate_safety_html_section(safety_findings))

            # Snyk Section (only if findings exist)
            if len(snyk_findings) > 0:
                f.write(generate_snyk_html_section(snyk_findings))

            # SonarQube Section (only if findings exist)
            if len(sonarqube_findings) > 0:
                f.write(generate_sonarqube_html_section(sonarqube_findings))

            # Terraform Security (Checkov) Section (only if findings exist)
            if len(checkov_findings) > 0:
                f.write(generate_terraform_checkov_html_section(checkov_findings))

            # Checkov Comprehensive Infrastructure Security Section (only if findings exist)
            if len(checkov_comprehensive_findings) > 0:
                f.write(generate_checkov_html_section(checkov_comprehensive_findings))

            # TruffleHog Section (only if findings exist)
            if len(trufflehog_findings) > 0:
                f.write(generate_trufflehog_html_section(trufflehog_findings))

            # GitLeaks Section (only if findings exist)
            if len(gitleaks_findings) > 0:
                f.write(generate_gitleaks_html_section(gitleaks_findings))

            # Detect-secrets Section (only if findings exist)
            if len(detect_secrets_findings) > 0:
                f.write(generate_detect_secrets_html_section(detect_secrets_findings))

            # npm audit Section (only if findings exist)
            if len(npm_audit_findings) > 0:
                f.write(generate_npm_audit_html_section(npm_audit_findings))

            # Wapiti Section (only if findings exist)
            if len(wapiti_findings) > 0:
                f.write(generate_wapiti_html_section(wapiti_findings))

            # Nikto Section (only if findings exist)
            if len(nikto_findings) > 0:
                f.write(generate_nikto_html_section(nikto_findings))

            # Burp Suite Section (only if findings exist)
            if len(burp_findings) > 0:
                f.write(generate_burp_html_section(burp_findings))

            # Kube-hunter Section (only if findings exist)
            if len(kube_hunter_findings) > 0:
                f.write(generate_kube_hunter_html_section(kube_hunter_findings))

            # Kube-bench Section (only if findings exist)
            if len(kube_bench_findings) > 0:
                f.write(generate_kube_bench_html_section(kube_bench_findings))

            # Docker Bench Section (only if findings exist)
            if len(docker_bench_findings) > 0:
                f.write(generate_docker_bench_html_section(docker_bench_findings))

            # ESLint Section (only if findings exist)
            if len(eslint_findings) > 0:
                f.write(generate_eslint_html_section(eslint_findings))

            # Clair Section (only if findings exist)
            if len(clair_vulns) > 0:
                f.write(generate_clair_html_section(clair_vulns))

            # Anchore Section (only if findings exist)
            if len(anchore_vulns) > 0:
                f.write(generate_anchore_html_section(anchore_vulns))

            # Brakeman Section (only if findings exist)
            if len(brakeman_findings) > 0:
                f.write(generate_brakeman_html_section(brakeman_findings))

            # Bandit Section (only if findings exist)
            if len(bandit_findings) > 0:
                f.write(generate_bandit_html_section(bandit_findings))

            f.write(html_footer())
        debug(f"HTML report successfully written to {OUTPUT_FILE}")
    except Exception as e:
        debug(f"Failed to write HTML report: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 