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
try:
    from core.path_setup import setup_paths, get_results_dir, get_output_file
    setup_paths()
except ImportError:
    # Fallback if core modules not available
    def setup_paths():
        pass
    def get_results_dir():
        return os.environ.get("RESULTS_DIR", "/app/results")
    def get_output_file():
        return os.environ.get("OUTPUT_FILE", "/app/results/security-summary.html")

try:
    from html_utils import html_header, html_footer, generate_executive_summary, generate_tool_status_section
except ImportError:
    # Fallback HTML functions
    def html_header(title, scripts, ai_disabled):
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .glass {{ background: rgba(255,255,255,0.1); border-radius: 8px; padding: 1rem; }}
    </style>
    {scripts}
</head>
<body>
    <h1>{title}</h1>
"""
    
    def html_footer():
        return "</body></html>"
    
    def generate_executive_summary(findings):
        return "<div class='glass'><h2>Executive Summary</h2><p>Summary not available.</p></div>"
    
    def generate_tool_status_section(tools):
        return "<div class='glass'><h2>Tool Status</h2><p>Tool status not available.</p></div>"

try:
    from processor_registry import ProcessorRegistry, register_default_processors
except ImportError:
    class ProcessorRegistry:
        @staticmethod
        def all():
            return []
    def register_default_processors():
        pass

try:
    from finding_policy import load_policy, apply_semgrep_policy, apply_gitleaks_policy, apply_bandit_policy
except ImportError:
    def load_policy(path):
        return {}
    def apply_semgrep_policy(findings, policy):
        return findings, []
    def apply_gitleaks_policy(findings, policy):
        return findings, []
    def apply_bandit_policy(findings, policy):
        return findings, []

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
    sys.stderr.write("[ERROR] This script must be called via the Python orchestrator or with RESULTS_DIR set.\n")
    sys.exit(1)

OUTPUT_FILE = get_output_file()
if not OUTPUT_FILE:
    sys.stderr.write("[ERROR] Could not determine OUTPUT_FILE!\n")
    sys.exit(1)

def debug(msg):
    print(f"[generate-html-report] {msg}", file=sys.stderr)

def read_json(path):
    """Robust JSON reader that handles missing files and parsing errors gracefully"""
    if not Path(path).exists():
        debug(f"Missing JSON file: {path}")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        debug(f"JSON decode error in {path}: {e}")
        return None
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
    
    # Project Information (host path removed for privacy/security)
    
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
        html_parts.append('<li style="margin-bottom: 0.5rem;">Run the scan with: <code>FINDING_POLICY_FILE=config/finding-policy.json python3 -m scanner.core.orchestrator</code></li>')
        html_parts.append('<li>Accepted findings will appear in the "Accepted Findings" section with your rationale</li>')
        html_parts.append('</ol>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('</details>')
    html_parts.append('</div>')
    
    return "".join(html_parts)

def normalize_findings_for_ai_prompt(processors, all_findings):
    """Normalize findings via processor registry for AI prompt generation."""
    normalized = []
    for processor in processors:
        if not processor.ai_normalizer:
            continue
        findings = all_findings.get(processor.name)
        if findings is None:
            continue
        normalized.extend(processor.ai_normalizer(findings))
    return normalized

def sanitize_findings(findings_by_tool):
    """Remove invalid non-dict entries from findings lists to prevent report crashes."""
    sanitized = {}
    for tool, findings in findings_by_tool.items():
        if isinstance(findings, list):
            cleaned = []
            for finding in findings:
                if isinstance(finding, dict):
                    cleaned.append(finding)
                else:
                    debug(
                        f"Skipping non-dict finding from {tool}: {type(finding).__name__} -> {finding}"
                    )
            sanitized[tool] = cleaned
        else:
            sanitized[tool] = findings
    return sanitized

def main():
    debug(f"Starting HTML report generation. Output: {OUTPUT_FILE}")
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    scan_type = os.environ.get('SCAN_TYPE', 'code')
    target_type = os.environ.get('TARGET_TYPE', '')
    
    # For code scans, use better target description
    if target_type in ('local_mount', 'git_repo', 'uploaded_code', '') and scan_type == 'code':
        # Try to get the actual project name from the results directory path
        # e.g., /app/results/NoServerConvert_20251026_170126 -> NoServerConvert
        results_path = RESULTS_DIR
        project_name = os.path.basename(results_path)
        if project_name and project_name != 'results':
            target = project_name.split('_')[0]  # Remove timestamp suffix
        else:
            target = 'Code scan'
    else:
        target = os.environ.get('SCAN_TARGET', 'Unknown')
    register_default_processors()
    processors = ProcessorRegistry.all()
    findings_by_tool = {}

    for processor in processors:
        if processor.html_file:
            html_path = os.path.join(RESULTS_DIR, processor.html_file)
            json_path = os.path.join(RESULTS_DIR, processor.json_file) if processor.json_file else None
            try:
                findings_by_tool[processor.name] = processor.summary_func(html_path, json_path)
            except Exception as e:
                debug(f"Warning: Could not process {processor.name} HTML file: {e}")
                findings_by_tool[processor.name] = None
        elif processor.json_file:
            json_path = os.path.join(RESULTS_DIR, processor.json_file)
            try:
                json_data = read_json(json_path)
                findings_by_tool[processor.name] = processor.summary_func(json_data)
            except Exception as e:
                debug(f"Warning: Could not process {processor.name} JSON file: {e}")
                findings_by_tool[processor.name] = None
        else:
            findings_by_tool[processor.name] = None
    accepted_findings = []
    semgrep_findings = findings_by_tool.get("Semgrep")
    gitleaks_findings = findings_by_tool.get("GitLeaks")
    bandit_findings = findings_by_tool.get("Bandit")

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
    
    if semgrep_findings is not None:
        semgrep_findings, semgrep_accepted = apply_semgrep_policy(semgrep_findings, finding_policy.get("semgrep", {}))
        findings_by_tool["Semgrep"] = semgrep_findings
        accepted_findings.extend(semgrep_accepted)
    if gitleaks_findings is not None:
        gitleaks_findings, gitleaks_accepted = apply_gitleaks_policy(gitleaks_findings, finding_policy.get("gitleaks", {}))
        findings_by_tool["GitLeaks"] = gitleaks_findings
        accepted_findings.extend(gitleaks_accepted)
    if bandit_findings is not None:
        bandit_findings, bandit_accepted = apply_bandit_policy(bandit_findings, finding_policy.get("bandit", {}))
        findings_by_tool["Bandit"] = bandit_findings
        accepted_findings.extend(bandit_accepted)

    try:
        all_findings = sanitize_findings(findings_by_tool)
        
        # Determine which tools were executed
        # A tool was executed if it has actual findings or if it was run but found nothing
        # We need to check if findings exist AND are not None
        # None means skipped, [] or items means executed but may have no findings
        executed_tools = {}
        for tool, findings in all_findings.items():
            # Tools that have findings (even if empty list) or ZAP with alerts should show as executed
            if findings is not None:
                executed_tools[tool] = {'status': 'complete'}
            elif tool == 'ZAP' and isinstance(findings, dict):
                executed_tools[tool] = {'status': 'complete'}
        
        # Read and embed JavaScript files inline (required for both Blob URLs and file://)
        embedded_scripts = ""
        js_files = ['ai_prompt_modal.js', 'webui.js']
        SCRIPT_DIR = Path(__file__).parent.absolute()  # scanner/output/
        
        # Try multiple possible locations for JS files (in order of preference)
        possible_dirs = [
            Path("/app/scanner/output"),  # Container absolute path (PRIMARY)
            SCRIPT_DIR,  # scanner/output/ (relative to script)
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
        
        # Normalize findings for AI prompt (for client-side generation when frontend is not available)
        normalized_findings = normalize_findings_for_ai_prompt(processors, all_findings)
        ai_prompt_disabled = len(normalized_findings) == 0
        findings_json = json.dumps(normalized_findings, indent=2)
        # Embed as JSON in script tag - no HTML escape needed since it's in a script tag
        # JSON is safe in script tags (no script execution)
        embedded_scripts += f'<script type="application/json" id="findings-data">{findings_json}</script>\n'
        debug(f"Embedded {len(normalized_findings)} normalized findings for AI prompt")
        
        # Generate HTML with robust error handling
        try:
            with open(OUTPUT_FILE, 'w') as f:
                f.write(html_header(f'{target} - {now}', embedded_scripts, ai_prompt_disabled))
                
                # Scan Metadata Section (only if metadata was collected)
                if scan_metadata:
                    f.write(generate_metadata_section(scan_metadata))

                # Executive Summary Dashboard
                f.write(generate_executive_summary(all_findings))

                # Tool execution status
                f.write(generate_tool_status_section(executed_tools))

                # Simple tool summary grid
                tool_cards = []
                for tool, findings in all_findings.items():
                    if findings is None:
                        continue
                    if tool == "ZAP" and isinstance(findings, dict):
                        count = sum(findings.get('summary', findings).values()) if isinstance(findings, dict) else 0
                    elif isinstance(findings, list):
                        count = len(findings)
                    else:
                        count = 0
                    tool_cards.append(f"<div class='tool-summary'><strong>{tool}</strong>: {count} findings</div>")
                if tool_cards:
                    f.write("<div class='summary-box'><h2>Tool Summary</h2>" + "".join(tool_cards) + "</div>")

                # Tool-specific sections
                for processor in processors:
                    findings = all_findings.get(processor.name)
                    if processor.html_func:
                        try:
                            if processor.name == "ZAP" and isinstance(findings, dict):
                                if sum(findings.get('summary', findings).values()) > 0:
                                    html_path = os.path.join(RESULTS_DIR, processor.html_file)
                                    f.write(processor.html_func(findings, html_path, Path, os))
                            elif findings is None:
                                continue
                            elif isinstance(findings, list) and len(findings) == 0:
                                continue
                            else:
                                f.write(processor.html_func(findings))
                        except Exception as e:
                            debug(f"Warning: Could not generate HTML for {processor.name}: {e}")
                            # Continue with other processors instead of failing completely
                            continue

                # Accepted Findings Section (only if policy accepted any findings)
                if len(accepted_findings) > 0:
                    f.write(generate_accepted_findings_section(accepted_findings))

                # Finding Policy Section (always shown - shows status or instructions)
                f.write(generate_finding_policy_section(finding_policy, policy_path, accepted_findings))

                f.write(html_footer())
            debug(f"HTML report successfully written to {OUTPUT_FILE}")
        except Exception as e:
            debug(f"Failed to write HTML report: {e}")
            traceback.print_exc()
            # Create a minimal fallback HTML report
            debug("Creating minimal fallback HTML report...")
            try:
                with open(OUTPUT_FILE, 'w') as f:
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{target} - {now} - Fallback Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error-box {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .tool-list {{ margin: 20px 0; }}
        .tool-item {{ margin: 5px 0; padding: 5px; }}
    </style>
</head>
<body>
    <h1>Security Scan Report - {target}</h1>
    <p><strong>Scan Date:</strong> {now}</p>
    
    <div class="error-box">
        <h3>⚠️ Report Generation Error</h3>
        <p>The full HTML report could not be generated due to an error. This is a minimal fallback report.</p>
        <p><strong>Error:</strong> {str(e)}</p>
    </div>
    
    <h2>Tool Execution Status</h2>
    <div class="tool-list">
        {"".join(f"<div class='tool-item'><strong>{tool}:</strong> {'Executed' if data.get('status') == 'complete' else 'Skipped'}</div>" for tool, data in executed_tools.items())}
    </div>
    
    <h2>Available Scanner Data</h2>
    <div class="tool-list">
        {"".join(f"<div class='tool-item'><strong>{tool}:</strong> {'Data available' if findings is not None else 'No data'}</div>" for tool, findings in all_findings.items())}
    </div>
    
    <p><em>For detailed results, please check the individual scanner output files in the results directory.</em></p>
</body>
</html>""")
                debug(f"Minimal fallback HTML report created at {OUTPUT_FILE}")
            except Exception as fallback_error:
                debug(f"Failed to create fallback HTML report: {fallback_error}")
                sys.exit(1)
    except Exception as e:
        debug(f"Failed to process findings: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 