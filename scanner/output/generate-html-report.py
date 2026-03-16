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
# Ensure scanner and app are first so core/scanner resolve to container /app/scanner (not /project/src)
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent  # scanner/
APP_DIR = SRC_DIR.parent      # /app in container
for p in (str(APP_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Use scanner.core so container always uses same code path (no /project/src)
from scanner.core.path_setup import setup_paths, get_results_dir, get_output_file
setup_paths()
# Re-insert app/scanner at front so later imports use container code
for p in (str(APP_DIR), str(SRC_DIR)):
    if sys.path[0] != p:
        sys.path.insert(0, p)

from scanner.output.html_utils import html_header, html_footer, generate_executive_summary, generate_tool_status_section
from scanner.core.finding_policy import load_policy
from scanner.core.scan_metadata import load_metadata

# Single source of truth: scanner names and paths come from ScannerRegistry only (required)
# Must use scanner.core.scanner_registry so plugin discovery uses the same module (same _scanners dict)
from scanner.core.scanner_registry import ScannerRegistry

# Get paths from central path_setup - NO PATH CALCULATIONS HERE!
_results_dir = get_results_dir()
if not _results_dir:
    sys.stderr.write("[ERROR] RESULTS_DIR environment variable is not set!\n")
    sys.stderr.write("[ERROR] This script must be called via the Python orchestrator or with RESULTS_DIR set.\n")
    sys.exit(1)
RESULTS_DIR = str(Path(_results_dir).resolve())

OUTPUT_FILE = get_output_file()
if not OUTPUT_FILE:
    sys.stderr.write("[ERROR] Could not determine OUTPUT_FILE!\n")
    sys.exit(1)

def debug(msg):
    print(f"[generate-html-report] {msg}", file=sys.stderr)

def _scanner_result_path(results_dir, tools_key, filename):
    """Path from registry only: results_dir/tools/<tools_key>/<filename>. tools_key comes from Scanner.tools_key."""
    if not filename or not tools_key:
        return None
    base = Path(results_dir)
    return str(base / "tools" / tools_key / filename)


def _get_processor_for_scanner(scanner):
    """Resolve report processor for a scanner from the same plugin (by python_class module path)."""
    if not getattr(scanner, "python_class", None):
        return None
    try:
        # e.g. "scanner.plugins.checkov.scanner.CheckovScanner" -> plugin "checkov"
        parts = scanner.python_class.split(".")
        if len(parts) >= 3 and parts[0] == "scanner" and parts[1] == "plugins":
            plugin_name = parts[2]
            processor_module = __import__(
                f"scanner.plugins.{plugin_name}.processor",
                fromlist=["REPORT_PROCESSOR"],
            )
            return getattr(processor_module, "REPORT_PROCESSOR", None)
    except Exception:
        pass
    return None


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


def generate_finding_policy_section(finding_policy, policy_path, accepted_findings, scanner_processors=None):
    """
    Generate expandable Finding Policy section.
    If no policy: example built from processors that have policy_example_snippet.
    If policy used: status + link to accepted findings.
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
        
        # Example JSON from processors that support policy (no hardcoded tool names)
        snippets = []
        if scanner_processors:
            for _, proc in scanner_processors:
                if getattr(proc, "policy_example_snippet", None):
                    snippets.append(proc.policy_example_snippet)
        example_json = "{\n" + ",\n".join(snippets) + "\n}" if snippets else "{}"
        html_parts.append('<details style="margin-top: 1rem;">')
        html_parts.append('<summary style="cursor: pointer; font-weight: 500; margin-bottom: 0.5rem; color: #0dcaf0;">📄 Example Policy Structure</summary>')
        html_parts.append('<pre style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; overflow-x: auto; margin-top: 0.5rem;"><code>')
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

def normalize_findings_for_ai_prompt(scanner_processors, all_findings):
    """Normalize findings for AI prompt. scanner_processors: list of (scanner, processor); all_findings keyed by scanner.name."""
    normalized = []
    for scanner, processor in (scanner_processors or []):
        if not processor or not getattr(processor, "ai_normalizer", None):
            continue
        findings = all_findings.get(scanner.name)
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


def load_tool_statuses_from_steps_log(results_dir):
    """
    Read steps.log (JSON Lines) and return a dict: tool_name -> {'status': 'complete'|'failed'|'skipped', 'message': str}.
    Only includes steps that correspond to scanners (names that appear as step names for scanner runs).
    """
    steps_log = Path(results_dir) / "logs" / "steps.log"
    if not steps_log.exists():
        return {}
    scanner_names = {s.name for s in ScannerRegistry.get_all_scanners()}
    tool_statuses = {}
    try:
        with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "init" in data:
                    continue
                name = data.get("name")
                status_str = data.get("status", "")
                message = data.get("message", "")
                if not name:
                    continue
                if name not in scanner_names:
                    continue
                if status_str == "completed":
                    tool_statuses[name] = {"status": "complete", "message": message or ""}
                elif status_str == "failed":
                    tool_statuses[name] = {"status": "failed", "message": message or ""}
                elif status_str == "skipped":
                    tool_statuses[name] = {"status": "skipped", "message": message or ""}
                elif status_str == "running":
                    tool_statuses[name] = {"status": "running", "message": message or ""}
                else:
                    tool_statuses[name] = {"status": "complete", "message": message or ""}
    except Exception as e:
        debug(f"Could not read steps.log: {e}")
    return tool_statuses

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
    # Single source of truth: use ScannerRegistry for tool names and paths; bind processor by plugin
    findings_by_tool = {}
    scanner_processors = []
    try:
        scanners = ScannerRegistry.get_all_scanners()
        for scanner in scanners:
            if not getattr(scanner, "tools_key", None):
                continue
            processor = _get_processor_for_scanner(scanner)
            if not processor:
                continue
            tool_name = scanner.name
            if processor.html_file:
                html_path = _scanner_result_path(RESULTS_DIR, scanner.tools_key, processor.html_file)
                json_path = _scanner_result_path(RESULTS_DIR, scanner.tools_key, processor.json_file) if processor.json_file else None
                path_to_check = Path(html_path) if html_path else None
            elif processor.json_file:
                json_path = _scanner_result_path(RESULTS_DIR, scanner.tools_key, processor.json_file)
                html_path = None
                path_to_check = Path(json_path) if json_path else None
            else:
                continue
            if path_to_check and not path_to_check.exists():
                continue
            try:
                if processor.html_file:
                    findings_by_tool[tool_name] = processor.summary_func(html_path or "", json_path)
                else:
                    json_data = read_json(json_path)
                    findings_by_tool[tool_name] = processor.summary_func(json_data) if json_data is not None else None
            except Exception as e:
                debug(f"Warning: Could not process {tool_name}: {e}")
                findings_by_tool[tool_name] = None
            scanner_processors.append((scanner, processor))
    except Exception as e:
        debug(f"ScannerRegistry failed: {e}")
        scanner_processors = []
        findings_by_tool = {}

    accepted_findings = []

    # Load scan metadata from results_dir/metadata/scan.json (not results_dir/scan.json)
    metadata_dir = os.path.join(RESULTS_DIR, "metadata")
    scan_metadata = load_metadata(metadata_dir)
    
    # Load finding policy: env FINDING_POLICY_FILE, then FINDING_POLICY_FILE_IN_CONTAINER, then metadata
    policy_path = os.environ.get("FINDING_POLICY_FILE", "").strip()
    if not policy_path:
        policy_path = os.environ.get("FINDING_POLICY_FILE_IN_CONTAINER", "").strip()
    if not policy_path and scan_metadata and scan_metadata.get("finding_policy"):
        policy_path = scan_metadata.get("finding_policy", "")
    
    if not policy_path or policy_path.strip() == "":
        finding_policy = {}
    else:
        finding_policy = load_policy(policy_path)
    
    for scanner, processor in scanner_processors:
        if not getattr(processor, "policy_key", None) or not getattr(processor, "apply_policy", None):
            continue
        findings = findings_by_tool.get(scanner.name)
        if findings is not None:
            tool_policy = finding_policy.get(processor.policy_key, {}) if isinstance(finding_policy, dict) else {}
            updated, accepted = processor.apply_policy(findings, tool_policy)
            findings_by_tool[scanner.name] = updated
            accepted_findings.extend(accepted)

    try:
        all_findings = sanitize_findings(findings_by_tool)
        
        # Determine which tools were executed: use steps.log for real status (complete/failed/skipped)
        executed_tools = load_tool_statuses_from_steps_log(RESULTS_DIR)
        for tool, findings in all_findings.items():
            if findings is not None or (tool == "ZAP" and isinstance(findings, dict)):
                executed_tools[tool] = {"status": "complete", "message": ""}
        
        # Read and embed JavaScript files inline (required for both Blob URLs and file://)
        embedded_scripts = ""
        js_files = ['ai_prompt_modal.js', 'webui.js']
        SCRIPT_DIR = Path(__file__).parent.absolute()  # scanner/output/
        
        # Try multiple possible locations for JS files (in order of preference)
        possible_dirs = [
            Path("/app/scanner/output"),  # Container absolute path (PRIMARY)
            SCRIPT_DIR,  # scanner/output/ (relative to script)
            Path(RESULTS_DIR),  # results/ (files copied after report generation)
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
        normalized_findings = normalize_findings_for_ai_prompt(scanner_processors, all_findings)
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

                # Tool-specific sections (scanner.name is the only key)
                for scanner, processor in scanner_processors:
                    tool_name = scanner.name
                    findings = all_findings.get(tool_name)
                    if not processor or not getattr(processor, "html_func", None):
                        continue
                    try:
                        if tool_name == "ZAP" and isinstance(findings, dict):
                            if sum(findings.get('summary', findings).values()) > 0:
                                html_path = _scanner_result_path(RESULTS_DIR, scanner.tools_key, processor.html_file)
                                f.write(processor.html_func(findings, html_path, Path, os))
                        elif findings is None:
                            continue
                        elif isinstance(findings, list) and len(findings) == 0:
                            continue
                        else:
                            f.write(processor.html_func(findings))
                    except Exception as e:
                        debug(f"Warning: Could not generate HTML for {tool_name}: {e}")
                        continue

                # Accepted Findings Section (only if policy accepted any findings)
                if len(accepted_findings) > 0:
                    f.write(generate_accepted_findings_section(accepted_findings))

                # Finding Policy Section (always shown - shows status or instructions)
                f.write(generate_finding_policy_section(finding_policy, policy_path, accepted_findings, scanner_processors))

                f.write(html_footer())
            debug(f"HTML report successfully written to {OUTPUT_FILE}")
        except Exception as e:
            debug(f"Failed to write HTML report: {e}")
            traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        debug(f"Failed to process findings: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 