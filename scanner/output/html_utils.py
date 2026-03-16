#!/usr/bin/env python3
import html as html_module

def html_header(title, embedded_scripts="", ai_prompt_disabled=False, overall_status=None, repo_url=None):
    # overall_status: "Critical" | "High" | "OK"; repo_url: optional link to repository
    badge_html = ""
    if overall_status:
        badge_class = "severity-badge-critical" if overall_status == "Critical" else "severity-badge-high" if overall_status == "High" else "severity-badge-ok"
        badge_html = f'<span class="severity-badge {badge_class}" title="Overall security status">{overall_status}</span>'
    repo_link_html = ""
    if repo_url and repo_url.strip():
        repo_esc = html_module.escape(repo_url.strip())
        repo_link_html = f'<a href="{repo_esc}" class="repo-link toggle-btn" target="_blank" rel="noopener noreferrer" title="Open repository">🔗 Open in GitHub</a>'
    return f'''<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>{title}</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="icon" type="image/png" href="assets/transparent.png">\n<style>\n
/* ============================================
   GLASSMORPHISM MODERN DESIGN
   (Frosted glass: backdrop-blur + semi-transparent surfaces)
   ============================================ */

:root {{
  --color-critical: #dc3545;
  --color-high: #fd7e14;
  --color-medium: #ffc107;
  --color-low: #0dcaf0;
  --color-info: #6c757d;
  --color-pass: #28a745;
  --bg-light: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  --bg-dark: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
  --text-light: #212529;
  --text-dark: #f8f9fa;
  --text-primary: #1a1a1a;
  --text-secondary: #495057;
  --border-radius: 16px;
  --shadow: 0 8px 32px rgba(0,0,0,0.1);
  --shadow-dark: 0 8px 32px rgba(0,0,0,0.3);
  --transition: all 0.3s ease;
  --glass-bg: rgba(255,255,255,0.25);
  --glass-bg-dark: rgba(0,0,0,0.25);
  --glass-border: rgba(255,255,255,0.18);
  --glass-border-dark: rgba(255,255,255,0.1);
  /* Modal (AI Prompt): readable, not too transparent */
  --modal-overlay: rgba(0, 0, 0, 0.75);
  --modal-content-bg: #1a1a2e;
  --modal-content-border: rgba(255, 255, 255, 0.12);
  --color-critical-bg: rgba(220, 53, 69, 0.2);
  --btn-primary: #667eea;
  --btn-primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}}


* {{
  box-sizing: border-box;
}}

body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  margin: 0;
  padding: 0;
  background: var(--bg-light);
  background-attachment: fixed;
  color: var(--text-light);
  transition: background 0.5s ease;
}}

body.dark {{
  background: var(--bg-dark);
  background-attachment: fixed;
  color: var(--text-dark);
  --text-primary: #f0f0f0;
  --text-secondary: #b0b0b0;
  --modal-content-bg: #1a1a2e;
  --modal-content-border: rgba(255, 255, 255, 0.12);
}}

/* Glassmorphism effect */
.glass {{
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: var(--border-radius);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow);
}}

body.dark .glass {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
  box-shadow: var(--shadow-dark);
}}

/* Header with glassmorphism */
.header {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--glass-border);
  padding: 2rem;
  box-shadow: 0 4px 30px rgba(0,0,0,0.1);
}}

body.dark .header {{
  background: var(--glass-bg-dark);
  border-bottom-color: var(--glass-border-dark);
}}

.header-content {{
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 2rem;
}}

h1 {{
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

body.dark h1 {{
  background: linear-gradient(135deg, #fff, #e0e0e0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

h2 {{ margin-top: 2em; }}

.scan-meta {{
  display: flex;
  gap: 1.5rem;
  font-size: 0.9rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}}

.scan-meta span {{
  background: var(--glass-bg-dark);
  backdrop-filter: blur(10px);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  border: 1px solid var(--glass-border);
}}

body.dark .scan-meta span {{
  background: var(--glass-bg);
  border-color: var(--glass-border-dark);
}}

.container {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}}

/* Executive Summary Cards */
.executive-summary {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}}

.summary-card {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow);
  transition: var(--transition);
  border-left: 4px solid;
  cursor: pointer;
}}

.summary-card:hover {{
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.15);
}}

body.dark .summary-card {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

.summary-card.critical {{ border-left-color: var(--color-critical); }}
.summary-card.high {{ border-left-color: var(--color-high); }}
.summary-card.medium {{ border-left-color: var(--color-medium); }}
.summary-card.passed {{ border-left-color: var(--color-pass); }}

.summary-card .number {{
  display: block;
  font-size: 3rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.5rem;
  color: inherit;
}}

.summary-card .label {{
  display: block;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.85;
  color: inherit;
}}

/* Domain scores row */
.domain-scores-grid {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}}
.domain-score-card {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  border-left: 3px solid;
  background: var(--glass-bg-dark);
  font-size: 0.85rem;
}}
body.dark .domain-score-card {{
  background: var(--glass-bg);
}}
.domain-score-card .domain-name {{
  opacity: 0.9;
}}
.domain-score-card .domain-score {{
  font-weight: 700;
}}

/* Tool Status Section */
.tool-status-section {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow);
}}

body.dark .tool-status-section {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

.tool-status-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}}

.tool-status-item {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--glass-bg-dark);
  border-radius: 8px;
  font-size: 0.85rem;
  border: 1px solid var(--glass-border);
  min-width: 0;
  overflow: hidden;
}}

body.dark .tool-status-item {{
  background: var(--glass-bg);
  border-color: var(--glass-border-dark);
}}

.tool-status-item .status-icon {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}}

.tool-status-item .tool-status-text {{
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  overflow: hidden;
}}

.tool-status-item .tool-name {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 0 1 auto;
}}

.tool-status-item .tool-msg {{
  font-size: 0.8rem;
  opacity: 0.9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1 1 0;
}}

.tool-status-item.status-complete .status-icon {{
  background: var(--color-pass);
}}

.tool-status-item.status-running .status-icon {{
  background: #ffc107;
  animation: pulse 1.5s ease-in-out infinite;
}}

.tool-status-item.status-failed .status-icon {{
  background: var(--color-critical);
}}

.tool-status-item.status-skipped .status-icon {{
  background: var(--color-info);
}}

@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}

/* Filter Bar */
.filter-bar {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  padding: 1rem 1.5rem;
  border-radius: var(--border-radius);
  margin-bottom: 2rem;
  box-shadow: var(--shadow);
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
  border: 1px solid var(--glass-border);
}}

body.dark .filter-bar {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

/* Legacy styles for compatibility */
.summary-box {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border-radius: var(--border-radius);
  padding: 1.5em;
  margin: 1.5em 0;
  border: 1px solid var(--glass-border);
}}

body.dark .summary-box {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

.tool-summary {{
  background: var(--glass-bg-dark);
  backdrop-filter: blur(10px);
  padding: 0.75rem;
  margin: 0.5rem 0;
  border-radius: 8px;
  border: 1px solid var(--glass-border);
}}

body.dark .tool-summary {{
  background: var(--glass-bg);
  border-color: var(--glass-border-dark);
}}

/* Severity colors */
.sev-CRITICAL {{ color: var(--color-critical); font-weight: bold; }}
.sev-HIGH {{ color: var(--color-high); font-weight: bold; }}
.sev-MEDIUM {{ color: var(--color-medium); font-weight: bold; }}
.sev-LOW {{ color: var(--color-low); }}
.sev-INFO, .sev-INFORMATIONAL {{ color: var(--color-info); }}
.sev-PASSED {{ color: var(--color-pass); font-weight: bold; }}

.icon {{ font-size: 1.2em; vertical-align: middle; margin-right: 0.3em; }}

/* Modern Grid Layout for Tools Summary */
.tools-grid-container {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1.5rem 0;
}}

.tool-category {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border-radius: var(--border-radius);
  padding: 0;
  border: 1px solid var(--glass-border);
  transition: all 0.3s ease;
  overflow: hidden;
}}

body.dark .tool-category {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

.tool-category > summary {{
  cursor: pointer;
  list-style: none;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  user-select: none;
  transition: background 0.2s ease;
  position: relative;
}}

.tool-category > summary:hover {{
  background: rgba(255, 255, 255, 0.05);
}}

.tool-category > summary::-webkit-details-marker {{
  display: none;
}}

.tool-category > summary::marker {{
  display: none;
}}

.tool-category > summary::after {{
  content: '▼';
  font-size: 0.7rem;
  margin-left: auto;
  transition: transform 0.3s ease;
  opacity: 0.5;
}}

.tool-category[open] > summary::after {{
  transform: rotate(180deg);
}}

.category-header {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
}}

.category-icon {{
  font-size: 1.2rem;
}}

.category-status-badge {{
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.8;
  font-style: italic;
}}

.tool-category[data-category-has-issues="true"] > summary {{
  border-left: 4px solid #ffc107;
}}

.tool-category[data-category-has-issues="false"] > summary {{
  border-left: 4px solid #28a745;
}}

.tool-category[data-category-has-issues="false"] summary .category-status-badge {{
  opacity: 0.6;
}}

.tools-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  padding: 1rem 1.5rem 1.5rem 1.5rem;
}}

.tool-card {{
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  padding: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
}}

.tool-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  border-color: var(--accent-primary);
}}

.tool-card.status-clean {{
  border-left: 3px solid #28a745;
  background: rgba(40, 167, 69, 0.05);
}}

.tool-card.status-issues {{
  border-left: 3px solid #ffc107;
  background: rgba(255, 193, 7, 0.1);
}}

.tool-card.status-skipped {{
  border-left: 3px solid #6c757d;
  background: rgba(108, 117, 125, 0.05);
  opacity: 0.7;
}}

.tool-card-header {{
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}}

.tool-name {{
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--text-primary);
}}

.tool-badge {{
  padding: 0.2rem 0.5rem;
  border-radius: 20px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  align-self: flex-start;
}}

.tool-count {{
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
}}

/* Add summary count display */
.tool-category[open] summary .category-status-badge::before,
.tool-category:not([open]) summary .category-status-badge::before {{
  content: attr(data-summary);
  display: inline-block;
}}

@media (max-width: 768px) {{
  .tools-grid {{
    grid-template-columns: 1fr;
  }}
  
  .category-header {{
    font-size: 0.9rem;
  }}
  
  .tool-card-header {{
    gap: 0.3rem;
  }}
  
  .tool-name {{
    font-size: 0.8rem;
  }}
}}

/* Table styles */
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  background: var(--glass-bg);
  color: inherit;
  border-radius: var(--border-radius);
  overflow: hidden;
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(10px);
}}

body.dark table {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

th, td {{
  border: 1px solid var(--glass-border);
  padding: 0.5em 1em;
  text-align: left;
}}

body.dark th, body.dark td {{
  border: 1px solid var(--glass-border-dark);
}}

a {{ color: #667eea; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Toggle button */
.toggle-btn {{
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  color: var(--text-light);
  padding: 0.75rem 1.5rem;
  border-radius: 30px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: var(--transition);
  font-weight: 500;
}}

.toggle-btn:hover {{
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}}

body.dark .toggle-btn {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
  color: var(--text-dark);
}}

/* Alert cards */
.alert-detail {{
  margin: 1.5em 0;
  padding: 1.5em;
  border: 2px solid var(--color-medium);
  background: var(--glass-bg);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  transition: var(--transition);
  backdrop-filter: blur(10px);
}}

.alert-detail:hover {{
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}}

body.dark .alert-detail {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

.alert-detail.high {{
  border-color: var(--color-high);
}}

.alert-detail.medium {{
  border-color: var(--color-medium);
}}

.alert-detail.low {{
  border-color: var(--color-low);
}}

.alert-detail.informational {{
  border-color: var(--color-info);
}}

.alert-detail h4 {{
  margin: 0 0 0.5em 0;
  font-size: 1.2em;
  font-weight: 600;
}}

.alert-meta {{
  display: flex;
  gap: 1em;
  margin-bottom: 1em;
  flex-wrap: wrap;
}}

.risk-badge {{
  padding: 0.3em 0.8em;
  border-radius: 20px;
  font-size: 0.9em;
  font-weight: 600;
  text-transform: uppercase;
}}

.risk-badge.high {{
  background: var(--color-high);
  color: white;
}}

.risk-badge.medium {{
  background: var(--color-medium);
  color: white;
}}

.risk-badge.low {{
  background: var(--color-low);
  color: white;
}}

.all-clear {{
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  color: var(--color-pass);
  border-radius: var(--border-radius);
  padding: 1em;
  margin: 1em 0;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 0.7em;
  font-size: 1.2em;
  border: 1px solid var(--glass-border);
}}

body.dark .all-clear {{
  background: var(--glass-bg-dark);
  border-color: var(--glass-border-dark);
}}

@media (max-width: 768px) {{
  .executive-summary {{
    grid-template-columns: 1fr;
  }}
  
  .header-content {{
    flex-direction: column;
    text-align: center;
  }}
  
  .scan-meta {{
    flex-direction: column;
    text-align: center;
  }}
}}

/* Severity badge in header – always high contrast (white text on colored bg) */
.severity-badge {{
  display: inline-block;
  margin-left: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  vertical-align: middle;
  color: #fff !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}}
.severity-badge-critical {{
  background: var(--color-critical);
}}
.severity-badge-high {{
  background: #e8590c;
  border: 1px solid rgba(255,255,255,0.2);
}}
.severity-badge-ok {{
  background: var(--color-pass);
}}
.repo-link {{
  text-decoration: none;
}}

/* Findings table: row background by severity */
.findings-table .finding-row.sev-CRITICAL {{ background: rgba(220, 53, 69, 0.15); }}
.findings-table .finding-row.sev-HIGH {{ background: rgba(253, 126, 20, 0.12); }}
.findings-table .finding-row.sev-MEDIUM {{ background: rgba(255, 193, 7, 0.1); }}
.findings-table .finding-row.sev-LOW {{ background: rgba(13, 202, 240, 0.08); }}
.findings-table .finding-row.sev-INFO {{ background: rgba(108, 117, 125, 0.06); }}
body.dark .findings-table .finding-row.sev-CRITICAL {{ background: rgba(220, 53, 69, 0.2); }}
body.dark .findings-table .finding-row.sev-HIGH {{ background: rgba(253, 126, 20, 0.18); }}
body.dark .findings-table .finding-row.sev-MEDIUM {{ background: rgba(255, 193, 7, 0.15); }}
body.dark .findings-table .finding-row.sev-LOW {{ background: rgba(13, 202, 240, 0.12); }}
body.dark .findings-table .finding-row.sev-INFO {{ background: rgba(108, 117, 125, 0.1); }}
.finding-icon {{
  font-size: 1em;
  vertical-align: middle;
  margin-right: 0.25rem;
}}

/* Scale down when opened directly (not in iframe) - larger viewports */
@media (min-width: 1400px) {{
  html {{
    font-size: 14px;
  }}
  
  body {{
    font-size: 14px;
  }}
  
  h1 {{
    font-size: 1.75rem;
  }}
  
  .container {{
    max-width: 1400px;
  }}
  
  .header {{
    padding: 1.5rem 2rem;
  }}
  
  .summary-card .number {{
    font-size: 2.5rem;
  }}
}}
</style>\n
<script>\n
function toggleDarkMode() {{
  document.body.classList.toggle('dark');
  localStorage.setItem('SimpleSecCheck-darkmode', document.body.classList.contains('dark'));
}}

window.onload = function() {{
  // Always default to dark mode
  document.body.classList.add('dark');
}};
</script>\n
{embedded_scripts}
</head>\n
<body>\n
<div class="header">\n
  <div class="header-content">\n
    <div>\n
      <h1>SimpleSecCheck Security Scan Summary {badge_html}</h1>\n
      <div class="scan-meta">\n
        <span>📅 {title}</span>\n
      </div>\n
    </div>\n
    <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">\n
      {repo_link_html}\n
      <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n
      <div id="ai-prompt-container" style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; padding: 0.5rem; background: rgba(255,255,255,0.12); border-radius: 8px; border: 1px solid var(--glass-border);">\n
        <button id="ai-prompt-btn" class="toggle-btn" onclick="generateAIPrompt()" style="background: linear-gradient(135deg, #6c757d, #495057);" {"disabled" if ai_prompt_disabled else ""} title="{ 'No findings available for AI prompt.' if ai_prompt_disabled else '' }">🤖 AI Prompt</button>\n
        {"<span style='opacity: 0.7; font-size: 0.85rem;'>No findings available</span>" if ai_prompt_disabled else ""}\n
      </div>\n
    </div>\n
  </div>\n
</div>\n
<div class="container">\n'''

def html_footer():
    return '</div>\n</body></html>'

# Enterprise severity weights and score thresholds
SEVERITY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 6,
    "MEDIUM": 3,
    "LOW": 1,
    "INFO": 0,
}
PENALTY_CAP = 60
SCORE_FLOOR = 10
SCORE_LABELS = [
    (90, "Excellent", "#28a745"),
    (75, "Good", "#28a745"),
    (60, "Moderate", "#ffc107"),
    (40, "Needs Attention", "#fd7e14"),
    (0, "Critical", "#dc3545"),
]

def _findings_as_list(findings):
    """Return findings as a list. Structure-based: dict with 'alerts' -> list of alerts; Trivy 'Results' -> flattened vulns; list -> list; else []. No tool names."""
    if findings is None:
        return []
    if isinstance(findings, list):
        return findings
    if isinstance(findings, dict):
        if "alerts" in findings:
            a = findings["alerts"]
            return a if isinstance(a, list) else []
        # Trivy report.json: {"Results": [{"Target": "...", "Vulnerabilities": [{...}]}]}
        if "Results" in findings:
            out = []
            for result in findings.get("Results", []) or []:
                target = result.get("Target", "")
                for v in result.get("Vulnerabilities", []) or []:
                    pkg = v.get("PkgName", "")
                    title = v.get("Title", "") or v.get("Description", "")
                    out.append({
                        "path": f"{target} | {pkg}" if target else pkg,
                        "file": pkg,
                        "PkgName": pkg,
                        "Severity": v.get("Severity", ""),
                        "VulnerabilityID": v.get("VulnerabilityID", ""),
                        "Title": title,
                        "message": title,
                        "rule_id": v.get("VulnerabilityID", ""),
                    })
            return out
    return []


def _findings_count(findings):
    """Return number of findings for display. Structure-based: list -> len; dict with 'alerts' -> len(alerts); dict with 'summary' -> sum(values); else 0. No tool names."""
    if findings is None:
        return 0
    if isinstance(findings, list):
        return len(findings)
    if isinstance(findings, dict):
        if "alerts" in findings and isinstance(findings["alerts"], list):
            return len(findings["alerts"])
        if "summary" in findings and isinstance(findings["summary"], dict):
            try:
                return sum(findings["summary"].values())
            except (TypeError, ValueError):
                return 0
    return 0


def _score_label_and_color(score):
    """Return (label, color) for a 0-100 score. Enterprise bands: 90+ Excellent, 75+ Good, 60+ Moderate, 40+ Needs Attention, 0-39 Critical."""
    for threshold, label, color in SCORE_LABELS:
        if score >= threshold:
            return label, color
    return "Critical", "#dc3545"


def _weighted_penalty(critical, high, medium, low, info):
    """Enterprise-style: severity-weighted penalty, capped."""
    total = (
        critical * SEVERITY_WEIGHTS["CRITICAL"]
        + high * SEVERITY_WEIGHTS["HIGH"]
        + medium * SEVERITY_WEIGHTS["MEDIUM"]
        + low * SEVERITY_WEIGHTS["LOW"]
        + info * SEVERITY_WEIGHTS["INFO"]
    )
    return min(total, PENALTY_CAP)


def generate_executive_summary(all_findings, domain_scores=None, executed_tools=None):
    """Generate executive dashboard with key metrics. Score = 100 - min(weighted_penalty, 60), floor 10. Enterprise bands for label.
    domain_scores: optional dict of domain_label -> score (0-100). executed_tools: optional dict tool -> {status, message}; when given, tools_executed/tools_passed are derived from it (passed = status 'complete') so the card matches the Scans Executed list."""
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    info_count = 0
    tools_executed = 0
    tools_passed = 0

    # When executed_tools is provided, use it for tool counts so "X/Y Tools Complete" matches the list (green = complete)
    if executed_tools:
        tools_executed = len(executed_tools)
        tools_passed = sum(
            1 for s in executed_tools.values()
            if isinstance(s, dict) and s.get("status") == "complete"
        )

    for tool, findings in all_findings.items():
        if findings is None:
            if not executed_tools:
                tools_executed += 1
                tools_passed += 1
            continue

        findings_list = _findings_as_list(findings)
        if not executed_tools:
            tools_executed += 1
            if len(findings_list) == 0:
                tools_passed += 1
        if len(findings_list) > 0:
            for finding in findings_list:
                if isinstance(finding, str):
                    medium_count += 1
                    continue
                if not isinstance(finding, dict):
                    print(
                        f"[html_utils] Skipping non-dict finding from {tool}: {type(finding).__name__} -> {finding}",
                        flush=True,
                    )
                    continue
                sev = str(finding.get("Severity", finding.get("severity", ""))).upper()
                if "CRITICAL" in sev or "CRIT" in sev:
                    critical_count += 1
                elif "HIGH" in sev or sev == "ERROR":
                    high_count += 1
                elif "MEDIUM" in sev or "MED" in sev or "WARN" in sev or "MODERATE" in sev:
                    medium_count += 1
                elif "LOW" in sev:
                    low_count += 1
                else:
                    info_count += 1

    # Enterprise overall score: 100 - min(weighted_penalty, 60), floor 10
    effective_penalty = _weighted_penalty(
        critical_count, high_count, medium_count, low_count, info_count
    )
    security_score = max(SCORE_FLOOR, int(100 - effective_penalty))
    score_label, score_color = _score_label_and_color(security_score)

    # Domain scores: render only what was passed (computed from registry scan_type in report generator)
    domain_section = ""
    if domain_scores:
        domain_cards = []
        for domain_label, dom_score in sorted(domain_scores.items()):
            _, dom_color = _score_label_and_color(dom_score)
            domain_cards.append(
                f'<div class="domain-score-card" style="border-left-color: {dom_color};"><span class="domain-name">{html_module.escape(domain_label)}</span><span class="domain-score" style="color: {dom_color};">{dom_score}</span></div>'
            )
        if domain_cards:
            domain_section = (
                '<div class="domain-scores" style="grid-column: 1/-1; margin-top: 0.5rem;">'
                '<div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; margin-bottom: 0.5rem;">Domain Scores</div>'
                '<div class="domain-scores-grid">'
                + "".join(domain_cards)
                + "</div></div>"
            )

    return f'''
    <div class="executive-summary">
      <div class="summary-card critical">
        <span class="number">{critical_count}</span>
        <span class="label">Critical Issues</span>
      </div>
      <div class="summary-card high">
        <span class="number">{high_count}</span>
        <span class="label">High Severity</span>
      </div>
      <div class="summary-card medium">
        <span class="number">{medium_count}</span>
        <span class="label">Medium Severity</span>
      </div>
      <div class="summary-card passed">
        <span class="number">{tools_passed}/{tools_executed}</span>
        <span class="label">Tools Complete</span>
      </div>
      <div class="summary-card" style="grid-column: 1/-1; text-align: center; border-left: 4px solid {score_color};">
        <div style="font-size: 2rem; font-weight: 700; color: {score_color};">{security_score} <span style="font-size: 1rem; font-weight: 400; opacity: 0.85;">/ 100</span></div>
        <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;">Security Score: {score_label}</div>
      </div>
      {domain_section}
    </div>
    '''

def generate_tool_status_section(executed_tools):
    """Generate section showing which scans were executed"""
    if not executed_tools:
        return ''
    
    tool_items = []
    for tool, status in sorted(executed_tools.items()):
        status_class = 'status-complete'  # Default complete
        if isinstance(status, dict) and status.get('status') == 'running':
            status_class = 'status-running'
        elif isinstance(status, dict) and status.get('status') == 'failed':
            status_class = 'status-failed'
        elif isinstance(status, dict) and status.get('status') == 'skipped':
            status_class = 'status-skipped'
        msg = (status.get('message', '') or '') if isinstance(status, dict) else ''
        msg_esc = html_module.escape(msg)
        msg_short = msg_esc[:60] + ("..." if len(msg_esc) > 60 else "")
        title_attr = f' title="{msg_esc}"' if msg else ''
        tool_items.append(f'''
          <div class="tool-status-item {status_class}"{title_attr}>
            <span class="status-icon"></span>
            <div class="tool-status-text">
              <span class="tool-name" title="{html_module.escape(tool)}">{html_module.escape(tool)}</span>
              {f'<span class="tool-msg">({msg_short})</span>' if msg else ''}
            </div>
          </div>
        ''')
    
    return f'''
    <div class="tool-status-section glass">
      <h3 style="margin-top: 0; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">🔍 Scans Executed</h3>
      <p style="margin: 0.5rem 0; opacity: 0.8;">The following security tools were executed during this scan:</p>
      <div class="tool-status-grid">
        {''.join(tool_items)}
      </div>
      <p style="margin-top: 1rem; font-size: 0.85rem; opacity: 0.7;">
        💡 <strong>Tip:</strong> Green = Complete | Yellow = Running | Red = Failed | Gray = Skipped
      </p>
    </div>
    '''
    