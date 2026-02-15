#!/usr/bin/env python3

def html_header(title):
    return f'''<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>{title}</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="icon" type="image/png" href="assets/transparent.png">\n<style>\n
/* ============================================
   GLASSMORPHISM MODERN DESIGN
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
  --border-radius: 16px;
  --shadow: 0 8px 32px rgba(0,0,0,0.1);
  --shadow-dark: 0 8px 32px rgba(0,0,0,0.3);
  --transition: all 0.3s ease;
  --glass-bg: rgba(255,255,255,0.25);
  --glass-bg-dark: rgba(0,0,0,0.25);
  --glass-border: rgba(255,255,255,0.18);
  --glass-border-dark: rgba(255,255,255,0.1);
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
}}

.summary-card .label {{
  display: block;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.8;
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
  padding: 0.5rem;
  background: var(--glass-bg-dark);
  border-radius: 8px;
  font-size: 0.85rem;
  border: 1px solid var(--glass-border);
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
<script src="webui.js"></script>\n
</head>\n
<body>\n
<div class="header">\n
  <div class="header-content">\n
    <div>\n
      <h1>SimpleSecCheck Security Scan Summary</h1>\n
      <div class="scan-meta">\n
        <span>📅 {title}</span>\n
      </div>\n
    </div>\n
    <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n
  </div>\n
</div>\n
<div class="container">\n'''

def html_footer():
    return '</div>\n</body></html>'

def generate_executive_summary(all_findings):
    """Generate executive dashboard with key metrics"""
    critical_count = 0
    high_count = 0
    medium_count = 0
    total_issues = 0
    tools_executed = 0
    tools_passed = 0
    
    for tool, findings in all_findings.items():
        if findings is None or len(findings) == 0:
            tools_executed += 1
            tools_passed += 1
        elif len(findings) > 0:
            tools_executed += 1
            total_issues += len(findings)
            
            # Count by severity
            for finding in findings:
                # Handle ZAP's structure (uses 'riskdesc')
                if 'riskdesc' in finding:
                    sev = str(finding.get('riskdesc', '')).upper()
                else:
                    # Standard structure - check both Severity and severity fields
                    sev = str(finding.get('Severity', finding.get('severity', ''))).upper()
                
                # Map to severity levels
                if 'CRITICAL' in sev or 'CRIT' in sev:
                    critical_count += 1
                elif 'HIGH' in sev:
                    high_count += 1
                elif 'MEDIUM' in sev or 'MED' in sev or 'WARN' in sev or 'MODERATE' in sev:
                    medium_count += 1
                elif 'INFO' in sev or 'INFORMATIONAL' in sev or 'LOW' in sev:
                    # Count low/info findings as medium for display purposes
                    medium_count += 1
    
    # Calculate security score (0-100)
    if tools_executed > 0:
        pass_rate = (tools_passed / tools_executed) * 100
        issue_penalty = min(total_issues * 2, 50)  # Max 50 point penalty
        security_score = max(int(pass_rate - issue_penalty), 0)
    else:
        security_score = 0
    
    score_color = '#28a745' if security_score >= 70 else '#ffc107' if security_score >= 40 else '#dc3545'
    score_label = 'Excellent' if security_score >= 70 else 'Good' if security_score >= 40 else 'Needs Attention'
    
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
        <span class="label">Tools Passed</span>
      </div>
      <div class="summary-card" style="grid-column: 1/-1; text-align: center; border-left: 4px solid {score_color};">
        <div style="font-size: 2rem; font-weight: 700; color: {score_color};">{security_score}</div>
        <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;">Security Score: {score_label}</div>
      </div>
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
        
        tool_items.append(f'''
          <div class="tool-status-item {status_class}">
            <span class="status-icon"></span>
            <span>{tool}</span>
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
        💡 <strong>Tip:</strong> Green = Complete | Yellow = Running | Red = Failed
      </p>
    </div>
    '''

# Legacy function for backward compatibility
def generate_visual_summary_section(zap_alerts, semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_findings, anchore_vulns, brakeman_findings, bandit_findings, android_findings=None, ios_findings=None):
    """Generate modern grid-based visual summary section with categorization"""
    
    # Categorize tools
    tool_categories = {
        'Static Code Analysis': [
            ('Semgrep', semgrep_findings if semgrep_findings else []),
            ('CodeQL', codeql_findings if codeql_findings else []),
            ('ESLint', eslint_findings if eslint_findings else []),
            ('Bandit', bandit_findings if bandit_findings else []),
            ('SonarQube', sonarqube_findings if sonarqube_findings else []),
            ('Brakeman', brakeman_findings if brakeman_findings else []),
        ],
        'Dependency & Package Security': [
            ('OWASP DC', owasp_dc_vulns if owasp_dc_vulns else []),
            ('npm audit', npm_audit_findings if npm_audit_findings else []),
            ('Safety', safety_findings if safety_findings else []),
            ('Snyk', snyk_findings if snyk_findings else []),
            ('Trivy', trivy_vulns if trivy_vulns else []),
        ],
        'Infrastructure as Code': [
            ('Checkov', checkov_findings if checkov_findings else []),
        ],
        'Secret Detection': [
            ('TruffleHog', trufflehog_findings if trufflehog_findings else []),
            ('GitLeaks', gitleaks_findings if gitleaks_findings else []),
            ('Detect-secrets', detect_secrets_findings if detect_secrets_findings else []),
        ],
        'Web Application Security': [
            ('ZAP', zap_alerts),
            ('Nuclei', nuclei_findings if nuclei_findings else []),
            ('Burp Suite', burp_findings if burp_findings else []),
            ('Wapiti', wapiti_findings if wapiti_findings else []),
            ('Nikto', nikto_findings if nikto_findings else []),
        ],
        'Container Security': [
            ('Clair', clair_findings if clair_findings else []),
            ('Anchore', anchore_vulns if anchore_vulns else []),
        ],
        'Kubernetes & Docker': [
            ('Kube-hunter', kube_hunter_findings if kube_hunter_findings else []),
            ('Kube-bench', kube_bench_findings if kube_bench_findings else []),
            ('Docker Bench', docker_bench_findings if docker_bench_findings else []),
        ],
    }
    
    html = '<div class="tools-grid-container">'
    
    for category, tools in tool_categories.items():
        category_html = []
        category_has_issues = False
        
        for tool_name, tool_findings in tools:
            # Handle ZAP's dict structure
            if tool_name == 'ZAP':
                count = sum(zap_alerts.values()) if isinstance(zap_alerts, dict) else 0
                # ZAP is considered executed if it exists
                is_skipped = not isinstance(zap_alerts, dict)
            else:
                count = len(tool_findings) if isinstance(tool_findings, list) else 0
                is_skipped = tool_findings is None
            
            # Check if tool was actually executed (not skipped)
            if is_skipped:
                status = 'skipped'
                status_class = 'status-skipped'
                status_text = 'Skipped'
                badge_color = '#6c757d'
                badge_icon = '⏭️'
            elif count == 0:
                status = 'clean'
                status_class = 'status-clean'
                status_text = 'Clean'
                badge_color = '#28a745'
                badge_icon = '✓'
                category_has_issues = False
            else:
                status = 'issues'
                status_class = 'status-issues'
                status_text = f'{count} issues'
                badge_color = '#ffc107'
                badge_icon = '⚠'
                category_has_issues = True
            
            category_html.append(f'''
            <div class="tool-card {status_class}" data-tool="{tool_name}">
              <div class="tool-card-header">
                <span class="tool-name">{tool_name}</span>
                <span class="tool-badge" style="background: {badge_color}20; color: {badge_color}; border: 1px solid {badge_color}40;">
                  {badge_icon} {status_text}
                </span>
              </div>
              <div class="tool-count">{count if count > 0 else 0} findings</div>
            </div>
            ''')
        
        # Only show category if it has at least one executed tool
        if category_html:
            category_id = category.lower().replace(' ', '-').replace('&', 'and')
            
            # Count total tools and tools with issues in this category
            tools_with_issues = sum(1 for item in category_html if 'status-issues' in item)
            total_tools = len(category_html)
            summary_text = f'({tools_with_issues}/{total_tools} with issues)' if tools_with_issues > 0 else f'({total_tools}/{total_tools} clean)'
            
            # Only set open attribute if category has issues
            open_attr = ' open' if category_has_issues else ''
            
            html += f'''
            <details class="tool-category" data-category-has-issues="{str(category_has_issues).lower()}"{open_attr} id="category-{category_id}">
              <summary class="category-header">
                <span class="category-icon">📦</span>
                {category}
                <span class="category-status-badge" data-summary="{summary_text}"></span>
              </summary>
              <div class="tools-grid">
                {''.join(category_html)}
              </div>
            </details>
            '''
    
    html += '</div>'
    return html

def generate_overall_summary_and_links_section(zap_alerts, semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_findings, anchore_vulns, brakeman_findings, bandit_findings, results_dir, path_module, os_module, android_findings=None, ios_findings=None):
    """Generate overall summary section (legacy)"""
    html_parts = []
    html_parts.append('<h2>Overall Summary</h2>\n')
    html_parts.append('<ul>')
    html_parts.append(f'<li>ZAP Alerts: {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Informational</li>')
    html_parts.append(f'<li>Semgrep Findings: {len(semgrep_findings) if semgrep_findings else 0}</li>')
    html_parts.append('</ul>')
    return "".join(html_parts) 
