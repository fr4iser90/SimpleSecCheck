#!/usr/bin/env python3
import inspect
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

from scanner.output.html_utils import (
    html_header,
    html_footer,
    generate_executive_summary,
    generate_tool_status_section,
    SEVERITY_WEIGHTS,
    PENALTY_CAP,
    SCORE_FLOOR,
    _weighted_penalty,
    _findings_as_list,
    _findings_count,
)
from scanner.core.finding_policy import load_policy
from scanner.core.scan_metadata import load_metadata

# Single source of truth: scanner names and paths come from ScannerRegistry only (required)
# Must use scanner.core.scanner_registry so plugin discovery uses the same module (same _scanners dict)
from scanner.core.scanner_registry import ScannerRegistry, ScanType

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
    Generate HTML section for scan metadata (only shown if metadata was collected). Collapsible.
    """
    if not metadata:
        return ""
    
    html_parts = []
    html_parts.append('<div class="glass report-section-collapsible" style="margin: 2rem 0; padding: 0; overflow: hidden;">')
    html_parts.append('<details class="tool-category" data-category-has-issues="false">')
    html_parts.append('<summary class="category-header"><span class="category-icon">📋</span> Scan Metadata</summary>')
    html_parts.append('<div style="padding: 2rem;">')
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
    html_parts.append('</div></details></div>')
    
    return "".join(html_parts)


def _severity_icon(sev):
    icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}
    return icons.get(sev, "ℹ️")


def generate_all_findings_section(report_findings):
    """Generate filterable/sortable All Findings table and filter bar. report_findings: list of {tool, severity, path, line, message, rule_id}."""
    if not report_findings:
        return '<div class="glass" style="margin: 2rem 0; padding: 1.5rem;"><h2>📋 All Findings</h2><p>No findings in this scan.</p></div>'

    tools = sorted({f["tool"] for f in report_findings})
    severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

    html_parts = [
        '<div class="glass report-section-collapsible" style="margin: 2rem 0; padding: 0; overflow: hidden;">',
        '<details open class="tool-category" data-category-has-issues="true">',
        '<summary class="category-header"><span class="category-icon">📋</span> All Findings</summary>',
        '<div style="padding: 1rem 1.5rem 1.5rem;">',
        # Filter bar
        '<div class="filter-bar" id="findings-filter-bar">',
        '<label>Tool: <select id="filter-tool"><option value="">All</option>',
    ]
    for t in tools:
        html_parts.append(f'<option value="{html.escape(t)}">{html.escape(t)}</option>')
    html_parts.append('</select></label>')
    html_parts.append('<label>Severity: <select id="filter-severity"><option value="">All</option>')
    for s in severities:
        html_parts.append(f'<option value="{html.escape(s)}">{html.escape(s)}</option>')
    html_parts.append('</select></label>')
    html_parts.append(
        '<label>Sort: <select id="sort-findings">'
        '<option value="severity">Severity</option><option value="tool">Tool</option><option value="path">File</option>'
        '</select></label>'
    )
    html_parts.append('<span id="findings-count" style="margin-left: auto; font-size: 0.9rem;"></span>')
    html_parts.append('</div>')
    # Table
    html_parts.append(
        '<table class="findings-table" id="findings-table">'
        '<thead><tr><th>Severity</th><th>Tool</th><th>File</th><th>Line</th><th>Rule / Message</th></tr></thead>'
        '<tbody id="findings-tbody">'
    )
    for f in report_findings:
        sev = f["severity"]
        icon = _severity_icon(sev)
        path_esc = html.escape(f["path"])
        line_esc = html.escape(f["line"])
        tool_esc = html.escape(f["tool"])
        msg_esc = html.escape(f["message"])[:200] + ("…" if len(f["message"]) > 200 else "")
        rule_esc = html.escape(f["rule_id"])
        title_attr = html.escape(f"{f['rule_id']}: {f['message'][:100]}")
        html_parts.append(
            f'<tr class="finding-row sev-{sev}" data-tool="{tool_esc}" data-severity="{sev}" data-path="{path_esc}" '
            f'data-line="{line_esc}" title="{title_attr}">'
            f'<td class="sev-{sev}"><span class="finding-icon" title="{title_attr}">{icon}</span> {sev}</td>'
            f'<td>{tool_esc}</td><td><code>{path_esc}</code></td><td>{line_esc}</td>'
            f'<td><span title="{html.escape(f["message"])}">{rule_esc}: {msg_esc}</span></td></tr>'
        )
    html_parts.append("</tbody></table>")
    html_parts.append("</div></details></div>")
    return "".join(html_parts)


def generate_accepted_findings_section(accepted_findings):
    if not accepted_findings:
        return ""

    html_parts = []
    html_parts.append(
        '<details class="tool-category report-section-collapsible" data-category-has-issues="false" id="accepted-findings-section">'
        '<summary class="category-header"><span class="category-icon">✅</span> Accepted Findings (With Rationale)</summary>'
        '<div style="padding: 1rem 1.5rem;">'
    )
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
    html_parts.append("</table></div></details>")
    return "".join(html_parts)


def generate_finding_policy_section(finding_policy, policy_path, accepted_findings, scanner_processors=None):
    """
    Generate expandable Finding Policy section.
    If no policy: example built from processors that have policy_example_snippet.
    If policy used: status + link to accepted findings.
    """
    html_parts = []
    html_parts.append('<div class="glass report-section-collapsible" style="margin: 2rem 0; padding: 0; overflow: hidden;">')
    
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
            html_parts.append('<a href="#accepted-findings-section" style="color: #0dcaf0; text-decoration: underline;">View accepted findings →</a>')
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
        html_parts.append('<li style="margin-bottom: 0.5rem;">Create a file named <code>finding-policy.json</code> in your project (e.g., <code>.scanning/finding-policy.json</code>)</li>')
        html_parts.append('<li style="margin-bottom: 0.5rem;">Use the example structure above as a template</li>')
        html_parts.append('<li style="margin-bottom: 0.5rem;">Run the scan with: <code>FINDING_POLICY_FILE=.scanning/finding-policy.json python3 -m scanner.core.orchestrator</code></li>')
        html_parts.append('<li>Accepted findings will appear in the "Accepted Findings" section with your rationale</li>')
        html_parts.append('</ol>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('</details>')
    html_parts.append('</div>')
    
    return "".join(html_parts)

def _normalize_severity(sev):
    """Map any severity string to CRITICAL|HIGH|MEDIUM|LOW|INFO."""
    if not sev:
        return "INFO"
    s = str(sev).upper()
    if "CRIT" in s:
        return "CRITICAL"
    if s == "HIGH" or s == "ERROR":
        return "HIGH"
    if s in ("MEDIUM", "MED", "WARN", "MODERATE"):
        return "MEDIUM"
    if s == "LOW":
        return "LOW"
    return "INFO"


def _normalize_finding_for_report(tool_name, finding):
    """Extract tool, severity, path, line, message, rule_id from any finding dict for report table."""
    if not isinstance(finding, dict):
        return None
    sev = str(finding.get("Severity", finding.get("severity", ""))).strip()
    path = str(finding.get("path", finding.get("file", finding.get("filename", finding.get("PkgName", "")))))
    line = finding.get("line") or finding.get("line_number") or (finding.get("start") if isinstance(finding.get("start"), (int, str)) else None)
    if line is None and isinstance(finding.get("start"), dict):
        line = finding["start"].get("line", "")
    line = str(line) if line is not None else ""
    message = str(finding.get("message", finding.get("issue_text", finding.get("description", finding.get("Description", finding.get("title", finding.get("Title", "")))))))
    rule_id = str(finding.get("rule_id", finding.get("check_id", finding.get("id", finding.get("VulnerabilityID", "")))))
    return {
        "tool": tool_name,
        "severity": _normalize_severity(sev),
        "path": path,
        "line": line,
        "message": message,
        "rule_id": rule_id,
    }


def build_report_findings(all_findings):
    """Build a flat list of normalized findings for filter/sort/export. Structure-based (dict with 'alerts' etc.), no tool names."""
    report_findings = []
    for tool, findings in all_findings.items():
        findings_list = _findings_as_list(findings)
        for f in findings_list:
            norm = _normalize_finding_for_report(tool, f)
            if norm:
                report_findings.append(norm)
    return report_findings


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


def _report_features_script():
    """Return inline script for filter, sort, export, expand/collapse in the standalone report."""
    return r"""
<script>
(function() {
  var SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };
  function getReportFindings() {
    var el = document.getElementById('report-findings-data');
    return el ? JSON.parse(el.textContent) : [];
  }
  function applyFilterAndSort() {
    var tbody = document.getElementById('findings-tbody');
    if (!tbody) return;
    var toolFilter = (document.getElementById('filter-tool') || {}).value || '';
    var sevFilter = (document.getElementById('filter-severity') || {}).value || '';
    var sortBy = (document.getElementById('sort-findings') || {}).value || 'severity';
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.finding-row'));
    rows.forEach(function(tr) {
      var show = (!toolFilter || tr.getAttribute('data-tool') === toolFilter) &&
                 (!sevFilter || tr.getAttribute('data-severity') === sevFilter);
      tr.style.display = show ? '' : 'none';
    });
    var visible = rows.filter(function(tr) { return tr.style.display !== 'none'; });
    var sorted = visible.slice().sort(function(a, b) {
      if (sortBy === 'severity') {
        var sa = SEV_ORDER[a.getAttribute('data-severity')] ?? 5;
        var sb = SEV_ORDER[b.getAttribute('data-severity')] ?? 5;
        if (sa !== sb) return sa - sb;
        var ta = (a.getAttribute('data-tool') || '').toLowerCase();
        var tb = (b.getAttribute('data-tool') || '').toLowerCase();
        if (ta !== tb) return ta < tb ? -1 : 1;
      } else if (sortBy === 'tool') {
        var ta = (a.getAttribute('data-tool') || '').toLowerCase();
        var tb = (b.getAttribute('data-tool') || '').toLowerCase();
        if (ta !== tb) return ta < tb ? -1 : 1;
        var sa = SEV_ORDER[a.getAttribute('data-severity')] ?? 5;
        var sb = SEV_ORDER[b.getAttribute('data-severity')] ?? 5;
        return sa - sb;
      } else if (sortBy === 'path') {
        var pa = (a.getAttribute('data-path') || '').toLowerCase();
        var pb = (b.getAttribute('data-path') || '').toLowerCase();
        if (pa !== pb) return pa < pb ? -1 : 1;
        var sa = SEV_ORDER[a.getAttribute('data-severity')] ?? 5;
        var sb = SEV_ORDER[b.getAttribute('data-severity')] ?? 5;
        return sa - sb;
      }
      return 0;
    });
    sorted.forEach(function(tr) { tbody.appendChild(tr); });
    var countEl = document.getElementById('findings-count');
    if (countEl) countEl.textContent = visible.length + ' of ' + rows.length + ' findings';
  }
  function downloadJSON() {
    var data = getReportFindings();
    var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'findings.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }
  function downloadCSV() {
    var data = getReportFindings();
    if (!data.length) return;
    var headers = ['tool', 'severity', 'path', 'line', 'rule_id', 'message'];
    var csv = headers.join(',') + '\n';
    data.forEach(function(f) {
      var row = headers.map(function(h) {
        var v = (f[h] != null ? f[h] : '');
        return '"' + String(v).replace(/"/g, '""') + '"';
      });
      csv += row.join(',') + '\n';
    });
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'findings.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }
  function expandAllSections() {
    document.querySelectorAll('.report-section-collapsible details, details.report-section-collapsible').forEach(function(d) { d.setAttribute('open', ''); });
  }
  function collapseAllSections() {
    document.querySelectorAll('.report-section-collapsible details, details.report-section-collapsible').forEach(function(d) { d.removeAttribute('open'); });
  }
  function initReportFeatures() {
    var tbody = document.getElementById('findings-tbody');
    if (tbody) {
      applyFilterAndSort();
      ['filter-tool', 'filter-severity', 'sort-findings'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('change', applyFilterAndSort);
      });
    }
    var btnJson = document.getElementById('export-json-btn');
    if (btnJson) btnJson.addEventListener('click', downloadJSON);
    var btnCsv = document.getElementById('export-csv-btn');
    if (btnCsv) btnCsv.addEventListener('click', downloadCSV);
    var btnExpand = document.getElementById('expand-all-btn');
    if (btnExpand) btnExpand.addEventListener('click', expandAllSections);
    var btnCollapse = document.getElementById('collapse-all-btn');
    if (btnCollapse) btnCollapse.addEventListener('click', collapseAllSections);
    var wrap = document.getElementById('copy-share-link-wrap');
    var btnShare = document.getElementById('copy-share-link-btn');
    if (wrap && btnShare) {
      if (window.location.protocol === 'file:' || window.parent === window) {
        wrap.style.display = 'none';
      } else {
        btnShare.addEventListener('click', function() {
          try { window.parent.postMessage({ type: 'SSC_COPY_SHARE_LINK' }, '*'); } catch (e) {}
        });
      }
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReportFeatures);
  } else {
    initReportFeatures();
  }
})();
</script>
"""


def _compute_tool_severity_counts(all_findings):
    """Compute per-tool severity counts (c, h, m, l, i) from all_findings. No hardcoded tool names."""
    result = {}
    for tool, findings in all_findings.items():
        findings_list = _findings_as_list(findings)
        c, h, m, l, i = 0, 0, 0, 0, 0
        for finding in findings_list:
            if not isinstance(finding, dict):
                continue
            sev = str(finding.get("Severity", finding.get("severity", ""))).upper()
            if "CRITICAL" in sev or "CRIT" in sev:
                c += 1
            elif "HIGH" in sev or sev == "ERROR":
                h += 1
            elif "MEDIUM" in sev or "MED" in sev or "WARN" in sev or "MODERATE" in sev:
                m += 1
            elif "LOW" in sev:
                l += 1
            else:
                i += 1
        result[tool] = (c, h, m, l, i)
    return result


def _compute_domain_scores(all_findings):
    """Compute domain scores from registry only: each ScanType aggregates tools that have that capability. No hardcoded tool names. Only includes domains that have at least one tool in this scan."""
    tool_severity = _compute_tool_severity_counts(all_findings)
    tools_in_scan = set(tool_severity.keys())
    domain_scores = {}
    for scan_type in ScanType:
        scanners = ScannerRegistry.get_scanners_for_type(scan_type)
        dc, dh, dm, dl, di = 0, 0, 0, 0, 0
        has_any = False
        for scanner in scanners:
            if scanner.name not in tools_in_scan:
                continue
            has_any = True
            c, h, m, l, i = tool_severity[scanner.name]
            dc, dh, dm, dl, di = dc + c, dh + h, dm + m, dl + l, di + i
        if not has_any:
            continue
        penalty = _weighted_penalty(dc, dh, dm, dl, di)
        score = max(SCORE_FLOOR, int(100 - penalty))
        label = scan_type.value.replace("_", " ").title()
        domain_scores[label] = score
    return domain_scores


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
            if findings is not None:
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

        # Report findings for filter/sort/export (flat list)
        report_findings = build_report_findings(all_findings)
        embedded_scripts += f'<script type="application/json" id="report-findings-data">{json.dumps(report_findings)}</script>\n'
        # Pre-fill AI prompt modal: policy path from scan (or default)
        display_policy_path = (policy_path or ".scanning/finding-policy.json").replace("/target/", "").strip()
        if not display_policy_path:
            display_policy_path = ".scanning/finding-policy.json"
        embedded_scripts += f'<script type="application/json" id="scan-ai-prompt-defaults">{json.dumps({"policy_path": display_policy_path})}</script>\n'
        embedded_scripts += _report_features_script()

        # Overall status for header badge: Critical | High | OK (counts are post-policy)
        def _sev(f, s):
            return 1 if (str(f.get("severity") or "").strip().upper() == s) else 0
        critical_count = sum(_sev(f, "CRITICAL") for f in report_findings)
        high_count = sum(_sev(f, "HIGH") for f in report_findings)
        medium_count = sum(_sev(f, "MEDIUM") for f in report_findings)
        low_count = sum(_sev(f, "LOW") for f in report_findings)
        info_count = sum(1 for f in report_findings if (str(f.get("severity") or "").strip().upper() in ("INFO", "INFORMATIONAL", "NOTE")))
        total_post_policy = len(report_findings)
        # Write post-policy statistics so worker/backend can store them (no false positives counted)
        statistics = {
            "total_vulnerabilities": total_post_policy,
            "critical_vulnerabilities": critical_count,
            "high_vulnerabilities": high_count,
            "medium_vulnerabilities": medium_count,
            "low_vulnerabilities": low_count,
            "info_vulnerabilities": info_count,
        }
        try:
            stats_path = Path(OUTPUT_FILE).parent / "statistics.json"
            with open(stats_path, "w", encoding="utf-8") as sf:
                json.dump(statistics, sf, indent=2)
            debug(f"Wrote post-policy statistics to {stats_path}")
        except Exception as e:
            debug(f"Warning: Could not write statistics.json: {e}")

        overall_status = "Critical" if critical_count > 0 else "High" if high_count > 0 else "OK"
        repo_url = ""
        if scan_metadata:
            repo_url = (scan_metadata.get("git_info") or {}).get("repository_url", "") or ""

        # Generate HTML with robust error handling
        try:
            with open(OUTPUT_FILE, 'w') as f:
                f.write(html_header(
                    f'{target} - {now}',
                    embedded_scripts,
                    ai_prompt_disabled,
                    overall_status=overall_status,
                    repo_url=repo_url,
                ))
                
                # Report actions: Expand/Collapse all, Export JSON/CSV
                f.write(
                    '<div class="filter-bar" style="margin-bottom: 1rem;">'
                    '<button type="button" class="toggle-btn" id="expand-all-btn">📂 Expand all</button> '
                    '<button type="button" class="toggle-btn" id="collapse-all-btn">📁 Collapse all</button> '
                    '<button type="button" class="toggle-btn" id="export-json-btn">📥 Download JSON</button> '
                    '<button type="button" class="toggle-btn" id="export-csv-btn">📥 Download CSV</button> '
                    '<span id="copy-share-link-wrap">'
                    '<button type="button" class="toggle-btn" id="copy-share-link-btn" '
                    'title="Copy shareable link (only when report is open inside the app)">🔗 Copy share link</button>'
                    '</span>'
                    '</div>'
                )

                # Scan Metadata Section (only if metadata was collected)
                if scan_metadata:
                    f.write(generate_metadata_section(scan_metadata))

                # Executive Summary Dashboard (domain_scores from registry ScanType only, no hardcoded tools)
                domain_scores = _compute_domain_scores(all_findings)
                f.write(generate_executive_summary(all_findings, domain_scores=domain_scores, executed_tools=executed_tools))

                # Tool execution status
                f.write(generate_tool_status_section(executed_tools))

                # Simple tool summary grid (structure-based count, no tool names)
                tool_cards = []
                for tool, findings in all_findings.items():
                    if findings is None:
                        continue
                    count = _findings_count(findings)
                    tool_cards.append(f"<div class='tool-summary'><strong>{html.escape(tool)}</strong>: {count} findings</div>")
                if tool_cards:
                    f.write("<div class='summary-box'><h2>Tool Summary</h2>" + "".join(tool_cards) + "</div>")

                # All Findings section (filter/sort table)
                f.write(generate_all_findings_section(report_findings))

                # Tool-specific sections (scanner.name is the only key), each wrapped in <details>
                for scanner, processor in scanner_processors:
                    tool_name = scanner.name
                    findings = all_findings.get(tool_name)
                    if not processor or not getattr(processor, "html_func", None):
                        continue
                    if findings is None or _findings_count(findings) == 0:
                        continue
                    try:
                        sig = inspect.signature(processor.html_func)
                        nparams = len(sig.parameters)
                        if nparams > 1:
                            html_path = _scanner_result_path(RESULTS_DIR, scanner.tools_key, processor.html_file) or ""
                            tool_html = processor.html_func(findings, html_path, Path, os)
                        else:
                            tool_html = processor.html_func(findings)
                        if tool_html:
                            f.write(
                                '<div class="glass report-section-collapsible" style="margin: 2rem 0; padding: 0; overflow: hidden;">'
                                '<details class="tool-category" data-category-has-issues="true">'
                                f'<summary class="category-header"><span class="category-icon">🔍</span> {html.escape(tool_name)}</summary>'
                                f'<div style="padding: 1rem 1.5rem;">{tool_html}</div>'
                                '</details></div>'
                            )
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