#!/usr/bin/env python3
import os
import json
import datetime
import sys
import html
from pathlib import Path
# Security: Use defusedxml instead of xml.etree to prevent XXE attacks
# defusedxml is a REQUIRED dependency - no fallback, script will fail if missing
from defusedxml.ElementTree import parse as safe_parse
from defusedxml import defuse_stdlib
defuse_stdlib()
import traceback

# Setup paths FIRST before importing anything from core
# Add src directory to path so we can import core modules
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent.absolute()
SRC_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SRC_DIR))

# Now we can import from core
from core.path_setup import setup_paths, get_results_dir, get_output_file
setup_paths()

from html_utils import html_header, html_footer, generate_visual_summary_section, generate_overall_summary_and_links_section, generate_executive_summary, generate_tool_status_section
from zap_processor import zap_summary, generate_zap_html_section
from zap_xml_parser import parse_zap_xml, generate_html_report
from semgrep_processor import semgrep_summary, generate_semgrep_html_section
from trivy_processor import trivy_summary, generate_trivy_html_section
from codeql_processor import codeql_summary, generate_codeql_html_section
from nuclei_processor import nuclei_summary, generate_nuclei_html_section
from owasp_dependency_check_processor import owasp_dependency_check_summary, generate_owasp_dependency_check_html_section
from safety_processor import safety_summary, generate_safety_html_section
from snyk_processor import snyk_summary, generate_snyk_html_section
from sonarqube_processor import sonarqube_summary, generate_sonarqube_html_section
from terraform_security_processor import checkov_summary as terraform_checkov_summary, generate_checkov_html_section as generate_terraform_checkov_html_section
from checkov_processor import checkov_summary, generate_checkov_html_section
from trufflehog_processor import trufflehog_summary, generate_trufflehog_html_section
from gitleaks_processor import gitleaks_summary, generate_gitleaks_html_section
from detect_secrets_processor import detect_secrets_summary, generate_detect_secrets_html_section
from npm_audit_processor import npm_audit_summary, generate_npm_audit_html_section
from wapiti_processor import wapiti_summary, generate_wapiti_html_section
from nikto_processor import nikto_summary, generate_nikto_html_section
from kube_hunter_processor import kube_hunter_summary, generate_kube_hunter_html_section
from kube_bench_processor import kube_bench_summary, generate_kube_bench_html_section
from docker_bench_processor import docker_bench_summary, generate_docker_bench_html_section
from eslint_processor import eslint_summary, generate_eslint_html_section
from clair_processor import clair_summary, generate_clair_html_section
from anchore_processor import anchore_summary, generate_anchore_html_section
from burp_processor import burp_summary, generate_burp_html_section
from brakeman_processor import brakeman_summary, generate_brakeman_html_section
from bandit_processor import bandit_summary, generate_bandit_html_section
from android_manifest_processor import android_manifest_summary, generate_android_manifest_html
from ios_plist_processor import ios_plist_summary, generate_ios_plist_html
from finding_policy import load_policy, apply_semgrep_policy, apply_gitleaks_policy, apply_bandit_policy
try:
    from scan_metadata import load_metadata
except ImportError:
    # Fallback if scan_metadata module not available (should not happen, but be safe)
    def load_metadata(results_dir):
        return None

# Get paths from central path_setup - NO PATH CALCULATIONS HERE!
RESULTS_DIR = get_results_dir()
if not RESULTS_DIR:
    sys.stderr.write("[ERROR] RESULTS_DIR environment variable is not set!\n")
    sys.stderr.write("[ERROR] This script must be called via security-check.sh or with RESULTS_DIR set.\n")
    sys.exit(1)

OUTPUT_FILE = get_output_file()
if not OUTPUT_FILE:
    sys.stderr.write("[ERROR] Could not determine OUTPUT_FILE!\n")
    sys.exit(1)

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


def generate_metadata_section(metadata):
    """
    Generate HTML section for scan metadata (only shown if metadata was collected).
    """
    if not metadata:
        return ""
    
    html_parts = []
    html_parts.append('<div class="glass" style="margin: 2rem 0; padding: 2rem;">')
    html_parts.append('<h2>📋 Scan Metadata</h2>')
    html_parts.append('<p style="color: #6c757d; margin-bottom: 1.5rem;">Metadata was collected because you enabled "Collect Metadata" option.</p>')
    html_parts.append('<table style="width: 100%; border-collapse: collapse;">')
    
    # Project Information
    if metadata.get("project_name"):
        html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; width: 30%;">Project Name:</td><td style="padding: 0.75rem;">{html.escape(str(metadata.get("project_name", "")))}</td></tr>')
    
    if metadata.get("target_path_absolute"):
        html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold;">Project Path:</td><td style="padding: 0.75rem; word-break: break-all;">{html.escape(str(metadata.get("target_path_absolute", "")))}</td></tr>')
    
    if metadata.get("scan_type"):
        html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold;">Scan Type:</td><td style="padding: 0.75rem;">{html.escape(str(metadata.get("scan_type", "")))}</td></tr>')
    
    # Git Information
    git_info = metadata.get("git_info", {})
    if git_info and any(git_info.values()):
        html_parts.append('<tr><td colspan="2" style="padding: 1rem 0.75rem 0.5rem; font-weight: bold; border-top: 1px solid rgba(255,255,255,0.2);">Git Repository Information:</td></tr>')
        
        if git_info.get("repository_url"):
            html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Repository URL:</td><td style="padding: 0.75rem; word-break: break-all;">{html.escape(str(git_info.get("repository_url", "")))}</td></tr>')
        
        if git_info.get("branch"):
            html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Branch:</td><td style="padding: 0.75rem;">{html.escape(str(git_info.get("branch", "")))}</td></tr>')
        
        if git_info.get("commit_hash"):
            html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Commit Hash:</td><td style="padding: 0.75rem; font-family: monospace;">{html.escape(str(git_info.get("commit_hash", "")))}</td></tr>')
        
        if git_info.get("commit_message"):
            html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Commit Message:</td><td style="padding: 0.75rem;">{html.escape(str(git_info.get("commit_message", "")))}</td></tr>')
        
        if git_info.get("is_dirty"):
            html_parts.append('<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Working Directory:</td><td style="padding: 0.75rem; color: #ffc107;">⚠️ Uncommitted changes detected</td></tr>')
    
    # Scan Configuration
    scan_config = metadata.get("scan_config", {})
    if scan_config:
        html_parts.append('<tr><td colspan="2" style="padding: 1rem 0.75rem 0.5rem; font-weight: bold; border-top: 1px solid rgba(255,255,255,0.2);">Scan Configuration:</td></tr>')
        
        if scan_config.get("finding_policy_used"):
            finding_policy_path = metadata.get("finding_policy", "")
            if finding_policy_path:
                # Remove /target/ prefix if present for display
                display_path = finding_policy_path.replace("/target/", "") if finding_policy_path.startswith("/target/") else finding_policy_path
                html_parts.append(f'<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Finding Policy:</td><td style="padding: 0.75rem;">✅ Enabled (<code style="background: rgba(0,0,0,0.2); padding: 0.2rem 0.5rem; border-radius: 4px;">{html.escape(display_path)}</code>)</td></tr>')
            else:
                html_parts.append('<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">Finding Policy:</td><td style="padding: 0.75rem;">✅ Enabled</td></tr>')
        
        if scan_config.get("ci_mode"):
            html_parts.append('<tr><td style="padding: 0.75rem; font-weight: bold; padding-left: 2rem;">CI Mode:</td><td style="padding: 0.75rem;">✅ Enabled</td></tr>')
    
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return "".join(html_parts)


def generate_accepted_findings_section(accepted_findings):
    if not accepted_findings:
        return ""

    html_parts = []
    html_parts.append('<h2 id="accepted-findings">Accepted Findings (With Rationale)</h2>')
    html_parts.append("<table><tr><th>Tool</th><th>ID</th><th>File</th><th>Line</th><th>Reason</th></tr>")
    for finding in accepted_findings:
        tool = html.escape(str(finding.get("tool", "")))
        fid = html.escape(str(finding.get("id", "")))
        path = html.escape(str(finding.get("path", "")))
        line = html.escape(str(finding.get("line", "")))
        reason = html.escape(str(finding.get("reason", "Accepted by policy")))
        html_parts.append(
            f"<tr><td>{tool}</td><td>{fid}</td><td>{path}</td><td>{line}</td><td>{reason}</td></tr>"
        )
    html_parts.append("</table>")
    return "".join(html_parts)


def generate_finding_policy_section(finding_policy, policy_path, accepted_findings):
    """
    Generate expandable Finding Policy section.
    Shows:
    - If NO policy: Example JSON structure + instructions
    - If policy used: Status + link to accepted findings
    """
    html_parts = []
    html_parts.append('<div class="glass" style="margin: 2rem 0; padding: 2rem;">')
    
    policy_used = bool(finding_policy and policy_path)
    has_accepted = len(accepted_findings) > 0
    
    # Expandable section using <details>/<summary> (like tool-category)
    html_parts.append('<details class="tool-category" data-category-has-issues="false" open>')
    html_parts.append('<summary class="category-header" style="cursor: pointer; user-select: none;">')
    
    if policy_used:
        html_parts.append('<h2 style="display: inline; margin: 0;">📋 Finding Policy</h2>')
        html_parts.append('<span class="category-status-badge" data-summary="✅ Active"></span>')
    else:
        html_parts.append('<h2 style="display: inline; margin: 0;">📋 Finding Policy</h2>')
        html_parts.append('<span class="category-status-badge" data-summary="ℹ️ Not configured"></span>')
    
    html_parts.append('</summary>')
    
    # Content
    html_parts.append('<div style="margin-top: 1.5rem; padding: 1rem; background: rgba(0,0,0,0.1); border-radius: 8px;">')
    
    if policy_used:
        # Policy is active
        html_parts.append('<p style="color: #28a745; font-weight: 500; margin-bottom: 1rem;">')
        html_parts.append('✅ A custom finding policy is active for this scan.')
        html_parts.append('</p>')
        
        html_parts.append(f'<p style="margin-bottom: 0.5rem;"><strong>Policy file:</strong> <code style="background: rgba(0,0,0,0.2); padding: 0.2rem 0.5rem; border-radius: 4px;">{html.escape(str(policy_path))}</code></p>')
        
        if has_accepted:
            html_parts.append('<p style="margin-top: 1rem; margin-bottom: 0.5rem;">')
            html_parts.append(f'<strong>Accepted findings:</strong> {len(accepted_findings)} finding(s) were accepted by the policy.')
            html_parts.append('</p>')
            html_parts.append('<p style="margin-top: 0.5rem;">')
            html_parts.append('<a href="#accepted-findings" style="color: #0dcaf0; text-decoration: underline;">View accepted findings →</a>')
            html_parts.append('</p>')
        else:
            html_parts.append('<p style="margin-top: 1rem; color: #6c757d;">No findings were accepted by the policy in this scan.</p>')
    else:
        # No policy - show instructions
        html_parts.append('<p style="color: #6c757d; margin-bottom: 1rem;">')
        html_parts.append('This project does not currently use a custom finding policy.')
        html_parts.append('</p>')
        
        html_parts.append('<p style="margin-bottom: 1.5rem;">')
        html_parts.append('If you want to suppress false positives or override severities, create a JSON-based finding policy file.')
        html_parts.append('</p>')
        
        # Example JSON (collapsible)
        html_parts.append('<details style="margin-top: 1rem;">')
        html_parts.append('<summary style="cursor: pointer; font-weight: 500; margin-bottom: 0.5rem; color: #0dcaf0;">📄 Example Policy Structure</summary>')
        html_parts.append('<pre style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; overflow-x: auto; margin-top: 0.5rem;"><code>')
        
        example_json = '''{
  "semgrep": {
    "severity_overrides": [
      {
        "rule_id": "python.django.security.debug-true.debug-true",
        "path_regex": "settings_dev\\.py$",
        "new_severity": "INFO",
        "reason": "DEBUG=True is intentional for development settings"
      }
    ],
    "accepted_findings": [
      {
        "rule_id": "generic.secrets.security.hardcoded-secret.hardcoded-secret",
        "path_regex": "src/examples/.*",
        "message_regex": "just_an_example",
        "reason": "This is an example key in a demonstration file, not a real secret"
      }
    ],
    "dedupe": {
      "enabled": true,
      "line_window": 2
    }
  },
  "gitleaks": {
    "accepted_findings": [
      {
        "rule_id": "generic-api-key",
        "file_regex": "tests/.*",
        "description_regex": "test.*key",
        "reason": "Test files contain example keys, not real secrets"
      }
    ]
  },
  "dedupe": {
    "enabled": true,
    "line_window": 2
  }
}'''
        html_parts.append(html.escape(example_json))
        html_parts.append('</code></pre>')
        html_parts.append('</details>')
        
        # Usage instructions
        html_parts.append('<div style="margin-top: 1.5rem; padding: 1rem; background: rgba(13, 202, 240, 0.1); border-left: 4px solid #0dcaf0; border-radius: 4px;">')
        html_parts.append('<p style="margin: 0; font-weight: 500; margin-bottom: 0.5rem;">💡 How to use:</p>')
        html_parts.append('<ol style="margin: 0.5rem 0 0 1.5rem; padding: 0;">')
        html_parts.append('<li style="margin-bottom: 0.5rem;">Create a file named <code>finding-policy.json</code> in your project (e.g., <code>config/finding-policy.json</code>)</li>')
        html_parts.append('<li style="margin-bottom: 0.5rem;">Use the example structure above as a template</li>')
        html_parts.append('<li style="margin-bottom: 0.5rem;">Run the scan with: <code>./run-docker.sh --finding-policy config/finding-policy.json /path/to/project</code></li>')
        html_parts.append('<li>Accepted findings will appear in the "Accepted Findings" section with your rationale</li>')
        html_parts.append('</ol>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('</details>')
    html_parts.append('</div>')
    
    return "".join(html_parts)

def normalize_findings_for_ai_prompt(all_findings):
    """
    Normalize findings from all tools to unified format for AI prompt generation.
    Returns list of normalized findings with tool, severity, path, line, message, rule_id.
    """
    normalized = []
    
    # Normalize each tool's findings
    for tool_name, findings in all_findings.items():
        if findings is None:
            continue
        
        # Handle different tool structures
        if tool_name == 'ZAP' and isinstance(findings, dict):
            # ZAP returns a dict with risk levels
            for risk_level, alerts in findings.items():
                if isinstance(alerts, list):
                    for alert in alerts:
                        normalized.append({
                            "tool": "ZAP",
                            "severity": risk_level.upper(),
                            "rule_id": str(alert.get("pluginid", "")),
                            "path": alert.get("uri", ""),
                            "line": "",
                            "message": alert.get("name", alert.get("alert", "")),
                        })
        elif isinstance(findings, list):
            # Standard list of findings
            for finding in findings:
                # Normalize based on tool
                if tool_name == "Semgrep":
                    normalized.append({
                        "tool": "Semgrep",
                        "severity": str(finding.get("severity", "UNKNOWN")).upper(),
                        "rule_id": str(finding.get("rule_id", "")),
                        "path": str(finding.get("path", "")),
                        "line": str(finding.get("start", finding.get("line", ""))),
                        "message": str(finding.get("message", "")),
                    })
                elif tool_name == "Trivy":
                    normalized.append({
                        "tool": "Trivy",
                        "severity": str(finding.get("Severity", "UNKNOWN")).upper(),
                        "rule_id": str(finding.get("VulnerabilityID", "")),
                        "path": str(finding.get("PkgName", "")),
                        "line": "",
                        "message": str(finding.get("Title", finding.get("Description", ""))),
                    })
                elif tool_name == "CodeQL":
                    normalized.append({
                        "tool": "CodeQL",
                        "severity": str(finding.get("severity", finding.get("level", "note"))).upper(),
                        "rule_id": str(finding.get("rule_id", finding.get("ruleId", ""))),
                        "path": str(finding.get("path", "")),
                        "line": str(finding.get("start", "")),
                        "message": str(finding.get("message", "")),
                    })
                elif tool_name == "GitLeaks":
                    normalized.append({
                        "tool": "GitLeaks",
                        "severity": "HIGH",
                        "rule_id": str(finding.get("rule_id", "")),
                        "path": str(finding.get("file", "")),
                        "line": str(finding.get("line", "")),
                        "message": str(finding.get("description", "")),
                    })
                elif tool_name == "TruffleHog":
                    normalized.append({
                        "tool": "TruffleHog",
                        "severity": "HIGH",
                        "rule_id": str(finding.get("detector", "")),
                        "path": str(finding.get("redacted", "")),
                        "line": "",
                        "message": str(finding.get("raw", ""))[:100] if finding.get("raw") else "",
                    })
                elif tool_name == "Detect-secrets":
                    normalized.append({
                        "tool": "Detect-secrets",
                        "severity": "HIGH" if finding.get("is_secret") else "MEDIUM",
                        "rule_id": str(finding.get("type", "")),
                        "path": str(finding.get("filename", "")),
                        "line": str(finding.get("line_number", "")),
                        "message": f"Secret type: {finding.get('type', '')}",
                    })
                elif tool_name == "OWASP Dependency Check":
                    normalized.append({
                        "tool": "OWASP Dependency Check",
                        "severity": str(finding.get("severity", "UNKNOWN")).upper(),
                        "rule_id": str(finding.get("name", "")),
                        "path": str(finding.get("fileName", "")),
                        "line": "",
                        "message": str(finding.get("description", "")),
                    })
                elif tool_name == "Safety":
                    normalized.append({
                        "tool": "Safety",
                        "severity": "HIGH",
                        "rule_id": str(finding.get("vulnerability", "")),
                        "path": str(finding.get("package", "")),
                        "line": "",
                        "message": str(finding.get("advisory", "")),
                    })
                elif tool_name == "Snyk":
                    normalized.append({
                        "tool": "Snyk",
                        "severity": str(finding.get("severity", "MEDIUM")).upper(),
                        "rule_id": str(finding.get("vulnerability_id", finding.get("id", ""))),
                        "path": str(finding.get("package", "")),
                        "line": "",
                        "message": str(finding.get("title", finding.get("description", ""))),
                    })
                elif tool_name == "ESLint":
                    severity_map = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
                    normalized.append({
                        "tool": "ESLint",
                        "severity": severity_map.get(finding.get("severity", 1), "LOW"),
                        "rule_id": str(finding.get("rule_id", "")),
                        "path": str(finding.get("file_path", "")),
                        "line": str(finding.get("line", "")),
                        "message": str(finding.get("message", "")),
                    })
                elif tool_name == "Brakeman":
                    normalized.append({
                        "tool": "Brakeman",
                        "severity": str(finding.get("severity", "MEDIUM")).upper(),
                        "rule_id": str(finding.get("warning_type", "")),
                        "path": str(finding.get("file", "")),
                        "line": str(finding.get("line", "")),
                        "message": str(finding.get("message", "")),
                    })
                elif tool_name == "Bandit":
                    normalized.append({
                        "tool": "Bandit",
                        "severity": str(finding.get("severity", "MEDIUM")).upper(),
                        "rule_id": str(finding.get("rule_id", "")),
                        "path": str(finding.get("filename", "")),
                        "line": str(finding.get("line_number", "")),
                        "message": str(finding.get("issue_text", "")),
                    })
                else:
                    # Generic normalization for other tools
                    normalized.append({
                        "tool": tool_name,
                        "severity": str(finding.get("severity", finding.get("Severity", "UNKNOWN"))).upper(),
                        "rule_id": str(finding.get("rule_id", finding.get("id", finding.get("rule_id", "")))),
                        "path": str(finding.get("path", finding.get("file", finding.get("filename", "")))),
                        "line": str(finding.get("line", finding.get("line_number", finding.get("start", "")))),
                        "message": str(finding.get("message", finding.get("description", finding.get("title", "")))),
                    })
    
    return normalized

def main():
    debug(f"Starting HTML report generation. Output: {OUTPUT_FILE}")
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    scan_type = os.environ.get('SCAN_TYPE', 'code')
    
    # For code scans, use better target description
    if scan_type == 'code':
        # Try to get the actual project name from the results directory path
        # e.g., /SimpleSecCheck/results/NoServerConvert_20251026_170126 -> NoServerConvert
        results_path = RESULTS_DIR
        project_name = os.path.basename(results_path)
        if project_name and project_name != 'results':
            target = project_name.split('_')[0]  # Remove timestamp suffix
        else:
            target = 'Code scan'
    else:
        target = os.environ.get('ZAP_TARGET', os.environ.get('TARGET_URL', 'Unknown'))
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
    android_manifest_json_path = os.path.join(RESULTS_DIR, 'android-manifest.json')
    ios_plist_json_path = os.path.join(RESULTS_DIR, 'ios-plist.json')

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
    android_findings_summary = android_manifest_summary(android_manifest_json_path)
    ios_findings_summary = ios_plist_summary(ios_plist_json_path)
    accepted_findings = []

    # Load scan metadata (only if user enabled metadata collection)
    scan_metadata = load_metadata(RESULTS_DIR)
    
    # Load finding policy - check environment variable first, then metadata
    policy_path = os.environ.get("FINDING_POLICY_FILE")
    if not policy_path or policy_path.strip() == "":
        # Try to get from metadata if available
        if scan_metadata and scan_metadata.get("finding_policy"):
            policy_path = scan_metadata.get("finding_policy")
    
    if not policy_path or policy_path.strip() == "":
        # No policy specified - don't use any policy
        finding_policy = {}
    else:
        # Policy was explicitly provided - try to load it
        finding_policy = load_policy(policy_path)
    
    semgrep_findings, semgrep_accepted = apply_semgrep_policy(semgrep_findings, finding_policy.get("semgrep", {}))
    gitleaks_findings, gitleaks_accepted = apply_gitleaks_policy(gitleaks_findings, finding_policy.get("gitleaks", {}))
    bandit_findings, bandit_accepted = apply_bandit_policy(bandit_findings, finding_policy.get("bandit", {}))
    accepted_findings.extend(semgrep_accepted)
    accepted_findings.extend(gitleaks_accepted)
    accepted_findings.extend(bandit_accepted)

    try:
        # Extract ZAP alerts list if available, otherwise use empty list
        zap_findings_list = zap_alerts.get('alerts', []) if isinstance(zap_alerts, dict) else []
        
        # Collect all findings for executive summary
        all_findings = {
            'ZAP': zap_findings_list,
            'Semgrep': semgrep_findings,
            'Trivy': trivy_vulns,
            'CodeQL': codeql_findings,
            'Nuclei': nuclei_findings,
            'OWASP DC': owasp_dc_vulns,
            'Safety': safety_findings,
            'Snyk': snyk_findings,
            'SonarQube': sonarqube_findings,
            'Checkov': checkov_comprehensive_findings,
            'TruffleHog': trufflehog_findings,
            'GitLeaks': gitleaks_findings,
            'Detect-secrets': detect_secrets_findings,
            'npm audit': npm_audit_findings,
            'Wapiti': wapiti_findings,
            'Nikto': nikto_findings,
            'Burp Suite': burp_findings,
            'Kube-hunter': kube_hunter_findings,
            'Kube-bench': kube_bench_findings,
            'Docker Bench': docker_bench_findings,
            'ESLint': eslint_findings,
            'Clair': clair_vulns,
            'Anchore': anchore_vulns,
            'Brakeman': brakeman_findings,
            'Bandit': bandit_findings,
            'Android': android_findings_summary,
            'iOS': ios_findings_summary,
        }
        
        # Determine which tools were executed
        # A tool was executed if it has actual findings or if it was run but found nothing
        # We need to check if findings exist AND are not None
        # None means skipped, [] or items means executed but may have no findings
        executed_tools = {}
        for tool, findings in all_findings.items():
            # Tools that have findings (even if empty list) or ZAP with alerts should show as executed
            if findings is not None:
                executed_tools[tool] = {'status': 'complete'}
            elif tool == 'ZAP' and isinstance(zap_alerts, dict):
                # ZAP returns a dict, not a list
                executed_tools[tool] = {'status': 'complete'}
        
        # Read and embed JavaScript files inline (required for both Blob URLs and file://)
        embedded_scripts = ""
        js_files = ['ai_prompt_modal.js', 'webui.js']
        SCRIPT_DIR = Path(__file__).parent.absolute()  # scanner/reporting/
        
        # Try multiple possible locations for JS files (in order of preference)
        possible_dirs = [
            Path("/SimpleSecCheck/scanner/reporting"),  # Container absolute path (PRIMARY)
            SCRIPT_DIR,  # scanner/reporting/ (relative to script)
            Path(RESULTS_DIR),  # results/ (fallback - files copied after report generation)
        ]
        
        for js_file in js_files:
            js_content = None
            found_path = None
            
            for base_dir in possible_dirs:
                js_path = base_dir / js_file
                if js_path.exists():
                    try:
                        with open(js_path, 'r', encoding='utf-8') as js_f:
                            js_content = js_f.read()
                            found_path = js_path
                            break
                    except Exception as e:
                        debug(f"Warning: Could not read {js_path}: {e}")
            
            if js_content:
                embedded_scripts += f"<script>\n{js_content}\n</script>\n"
                debug(f"Embedded {js_file} from {found_path}")
            else:
                debug(f"ERROR: {js_file} not found in any of: {possible_dirs}")
                # Don't exit - continue without JS, but log error
                sys.stderr.write(f"[ERROR] Failed to embed {js_file} - AI Prompt feature will not work!\n")
        
        # Normalize findings for AI prompt (for client-side generation when WebUI is not available)
        normalized_findings = normalize_findings_for_ai_prompt(all_findings)
        findings_json = json.dumps(normalized_findings, indent=2)
        # Embed as JSON in script tag - no HTML escape needed since it's in a script tag
        # JSON is safe in script tags (no script execution)
        embedded_scripts += f'<script type="application/json" id="findings-data">{findings_json}</script>\n'
        debug(f"Embedded {len(normalized_findings)} normalized findings for AI prompt")
        
        with open(OUTPUT_FILE, 'w') as f:
            f.write(html_header(f'{target} - {now}', embedded_scripts))
            # WebUI Controls Block
            # WebUI Controls removed - using single-shot scans only

            # Scan Metadata Section (only if metadata was collected)
            if scan_metadata:
                f.write(generate_metadata_section(scan_metadata))

            # Executive Summary Dashboard
            f.write(generate_executive_summary(all_findings))

            # --- Visual summary with icons/colors for each tool ---
            f.write(generate_visual_summary_section(zap_alerts.get('summary', zap_alerts), semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_comprehensive_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_vulns, anchore_vulns, brakeman_findings, bandit_findings, android_findings_summary, ios_findings_summary))

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

            # Snyk Section - show if skipped (None) or if there are findings
            if snyk_findings is None or len(snyk_findings) > 0:
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

            # Accepted Findings Section (only if policy accepted any findings)
            if len(accepted_findings) > 0:
                f.write(generate_accepted_findings_section(accepted_findings))

            # Finding Policy Section (always shown - shows status or instructions)
            f.write(generate_finding_policy_section(finding_policy, policy_path, accepted_findings))

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

            # Android Manifest Section (only if findings exist)
            android_html = generate_android_manifest_html(android_manifest_json_path)
            if android_html:
                f.write(android_html)

            # iOS Plist Section (only if findings exist)
            ios_html = generate_ios_plist_html(ios_plist_json_path)
            if ios_html:
                f.write(ios_html)

            f.write(html_footer())
        debug(f"HTML report successfully written to {OUTPUT_FILE}")
    except Exception as e:
        debug(f"Failed to write HTML report: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 