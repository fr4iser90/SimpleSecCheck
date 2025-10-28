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
  /* Dark mode alert backgrounds */
  --sev-bg-critical-dark: #742a2a;
  --sev-bg-high-dark: #744210;
  --sev-bg-medium-dark: #744210;
  --sev-bg-low-dark: #2a4365;
  --sev-bg-info-dark: #4a5568;
}}
body {{
  background: var(--bg-light);
  color: var(--text-light);
  font-family: 'Segoe UI', Arial, sans-serif;
  margin: 0; padding: 0;
  transition: background 0.2s, color 0.2s;
}}
body.lightmode {{
  background: var(--bg-light);
  color: var(--text-light);
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
body.lightmode .header {{
  background: var(--bg-light);
  border-bottom: 1px solid var(--table-border);
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
/* --- Alert Detail Cards --- */
.alert-detail {{
  margin: 1.5em 0;
  padding: 1.5em;
  border: 2px solid var(--sev-medium);
  background: var(--sev-bg-medium);
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}}
.alert-detail:hover {{
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}}
.alert-detail.high {{
  border-color: var(--sev-high);
  background: var(--sev-bg-high);
}}
.alert-detail.medium {{
  border-color: var(--sev-medium);
  background: var(--sev-bg-medium);
}}
.alert-detail.low {{
  border-color: var(--sev-low);
  background: var(--sev-bg-low);
}}
.alert-detail.informational {{
  border-color: var(--sev-info);
  background: var(--sev-bg-info);
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
  background: var(--sev-high);
  color: white;
}}
.risk-badge.medium {{
  background: var(--sev-medium);
  color: white;
}}
.risk-badge.low {{
  background: var(--sev-low);
  color: white;
}}
.risk-badge.informational {{
  background: var(--sev-info);
  color: white;
}}
.alert-count {{
  padding: 0.3em 0.8em;
  background: #f8f9fa;
  border-radius: 20px;
  font-size: 0.9em;
  font-weight: 500;
}}
body.darkmode .alert-count {{
  background: #343a40;
  color: var(--text-dark);
}}
body.darkmode .alert-detail {{
  background: var(--sev-bg-medium-dark);
  border-color: #4a5568;
}}
body.darkmode .alert-detail.high {{
  background: var(--sev-bg-high-dark);
  border-color: var(--sev-high);
}}
body.darkmode .alert-detail.medium {{
  background: var(--sev-bg-medium-dark);
  border-color: var(--sev-medium);
}}
body.darkmode .alert-detail.low {{
  background: var(--sev-bg-low-dark);
  border-color: var(--sev-low);
}}
body.darkmode .alert-detail.informational {{
  background: var(--sev-bg-info-dark);
  border-color: var(--sev-info);
}}
.alert-description, .alert-solution {{
  margin: 1em 0;
}}
.alert-description p, .alert-solution p {{
  margin: 0.5em 0;
  line-height: 1.6;
}}
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
  // Always default to dark mode
  document.body.classList.add('darkmode');
}};
</script>\n<script src="webui.js"></script>\n</head>\n<body>\n<div class="header">\n  <h1>SimpleSecCheck Security Scan Summary</h1>\n  <button class="toggle-btn" onclick="toggleDarkMode()">🌙/☀️ Toggle Dark/Light</button>\n</div>\n<div class="summary-box">'''

def html_footer():
    # Content of html_footer function (lines 299-300 from the original generate-html-report.py)
    return '</div>\n</body></html>'

def generate_visual_summary_section(zap_alerts, semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_findings, anchore_vulns, brakeman_findings, bandit_findings, android_findings=None, ios_findings=None):
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
    
    # CodeQL Visual Summary
    if len(codeql_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>CodeQL:</b> No findings</div>')
    else:
        codeql_counts = {"ERROR": 0, "WARNING": 0, "NOTE": 0, "INFO": 0}
        for f in codeql_findings:
            sev = f['severity'].upper()
            if sev in codeql_counts:
                codeql_counts[sev] += 1
        codeql_icon = '✅' if sum(codeql_counts.values()) == 0 else ''
        if codeql_counts['ERROR'] > 0:
            codeql_icon = '🚨'
        elif codeql_counts['WARNING'] > 0:
            codeql_icon = '⚠️'
        elif codeql_counts['NOTE'] > 0 or codeql_counts['INFO'] > 0:
            codeql_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"ERROR" if codeql_counts["ERROR"]>0 else ("WARNING" if codeql_counts["WARNING"]>0 else ("NOTE" if codeql_counts["NOTE"]>0 else ("INFO" if codeql_counts["INFO"]>0 else "PASSED")))}">{codeql_icon}</span> <b>CodeQL:</b> {codeql_counts["ERROR"]} Error, {codeql_counts["WARNING"]} Warning, {codeql_counts["NOTE"]} Note, {codeql_counts["INFO"]} Info</div>')
    
    # Nuclei Visual Summary
    if len(nuclei_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Nuclei:</b> No findings</div>')
    else:
        nuclei_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in nuclei_findings:
            sev = f['severity'].upper()
            if sev in nuclei_counts:
                nuclei_counts[sev] += 1
        nuclei_icon = '✅' if sum(nuclei_counts.values()) == 0 else ''
        if nuclei_counts['CRITICAL'] > 0:
            nuclei_icon = '🚨'
        elif nuclei_counts['HIGH'] > 0:
            nuclei_icon = '🚨'
        elif nuclei_counts['MEDIUM'] > 0:
            nuclei_icon = '⚠️'
        elif nuclei_counts['LOW'] > 0 or nuclei_counts['INFO'] > 0:
            nuclei_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if nuclei_counts["CRITICAL"]>0 else ("HIGH" if nuclei_counts["HIGH"]>0 else ("MEDIUM" if nuclei_counts["MEDIUM"]>0 else ("LOW" if nuclei_counts["LOW"]>0 else ("INFO" if nuclei_counts["INFO"]>0 else "PASSED"))))}">{nuclei_icon}</span> <b>Nuclei:</b> {nuclei_counts["CRITICAL"]} Critical, {nuclei_counts["HIGH"]} High, {nuclei_counts["MEDIUM"]} Medium, {nuclei_counts["LOW"]} Low, {nuclei_counts["INFO"]} Info</div>')
    
    # OWASP Dependency Check Visual Summary
    if len(owasp_dc_vulns) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>OWASP Dependency Check:</b> No vulnerabilities</div>')
    else:
        owasp_dc_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for v in owasp_dc_vulns:
            sev = v['Severity'].upper()
            if sev in owasp_dc_counts:
                owasp_dc_counts[sev] += 1
        owasp_dc_icon = '✅' if sum(owasp_dc_counts.values()) == 0 else ''
        if owasp_dc_counts['CRITICAL'] > 0:
            owasp_dc_icon = '🚨'
        elif owasp_dc_counts['HIGH'] > 0:
            owasp_dc_icon = '🚨'
        elif owasp_dc_counts['MEDIUM'] > 0:
            owasp_dc_icon = '⚠️'
        elif owasp_dc_counts['LOW'] > 0 or owasp_dc_counts['INFO'] > 0:
            owasp_dc_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if owasp_dc_counts["CRITICAL"]>0 else ("HIGH" if owasp_dc_counts["HIGH"]>0 else ("MEDIUM" if owasp_dc_counts["MEDIUM"]>0 else ("LOW" if owasp_dc_counts["LOW"]>0 else ("INFO" if owasp_dc_counts["INFO"]>0 else "PASSED"))))}">{owasp_dc_icon}</span> <b>OWASP Dependency Check:</b> {owasp_dc_counts["CRITICAL"]} Critical, {owasp_dc_counts["HIGH"]} High, {owasp_dc_counts["MEDIUM"]} Medium, {owasp_dc_counts["LOW"]} Low, {owasp_dc_counts["INFO"]} Info</div>')
    
    # Safety Visual Summary
    if len(safety_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Safety:</b> No vulnerabilities</div>')
    else:
        safety_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in safety_findings:
            sev = f['severity'].upper()
            if sev in safety_counts:
                safety_counts[sev] += 1
        safety_icon = '✅' if sum(safety_counts.values()) == 0 else ''
        if safety_counts['CRITICAL'] > 0:
            safety_icon = '🚨'
        elif safety_counts['HIGH'] > 0:
            safety_icon = '🚨'
        elif safety_counts['MEDIUM'] > 0:
            safety_icon = '⚠️'
        elif safety_counts['LOW'] > 0 or safety_counts['INFO'] > 0:
            safety_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if safety_counts["CRITICAL"]>0 else ("HIGH" if safety_counts["HIGH"]>0 else ("MEDIUM" if safety_counts["MEDIUM"]>0 else ("LOW" if safety_counts["LOW"]>0 else ("INFO" if safety_counts["INFO"]>0 else "PASSED"))))}">{safety_icon}</span> <b>Safety:</b> {safety_counts["CRITICAL"]} Critical, {safety_counts["HIGH"]} High, {safety_counts["MEDIUM"]} Medium, {safety_counts["LOW"]} Low, {safety_counts["INFO"]} Info</div>')
    
    # Snyk Visual Summary
    if len(snyk_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Snyk:</b> No vulnerabilities</div>')
    else:
        snyk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in snyk_findings:
            sev = f['severity'].upper()
            if sev in snyk_counts:
                snyk_counts[sev] += 1
        snyk_icon = '✅' if sum(snyk_counts.values()) == 0 else ''
        if snyk_counts['CRITICAL'] > 0:
            snyk_icon = '🚨'
        elif snyk_counts['HIGH'] > 0:
            snyk_icon = '🚨'
        elif snyk_counts['MEDIUM'] > 0:
            snyk_icon = '⚠️'
        elif snyk_counts['LOW'] > 0 or snyk_counts['INFO'] > 0:
            snyk_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if snyk_counts["CRITICAL"]>0 else ("HIGH" if snyk_counts["HIGH"]>0 else ("MEDIUM" if snyk_counts["MEDIUM"]>0 else ("LOW" if snyk_counts["LOW"]>0 else ("INFO" if snyk_counts["INFO"]>0 else "PASSED"))))}">{snyk_icon}</span> <b>Snyk:</b> {snyk_counts["CRITICAL"]} Critical, {snyk_counts["HIGH"]} High, {snyk_counts["MEDIUM"]} Medium, {snyk_counts["LOW"]} Low, {snyk_counts["INFO"]} Info</div>')
    
    # SonarQube Visual Summary
    if len(sonarqube_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>SonarQube:</b> No findings</div>')
    else:
        sonarqube_counts = {"BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0}
        for f in sonarqube_findings:
            sev = f['severity'].upper()
            if sev in sonarqube_counts:
                sonarqube_counts[sev] += 1
        sonarqube_icon = '✅' if sum(sonarqube_counts.values()) == 0 else ''
        if sonarqube_counts['BLOCKER'] > 0 or sonarqube_counts['CRITICAL'] > 0:
            sonarqube_icon = '🚨'
        elif sonarqube_counts['MAJOR'] > 0:
            sonarqube_icon = '⚠️'
        elif sonarqube_counts['MINOR'] > 0 or sonarqube_counts['INFO'] > 0:
            sonarqube_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if sonarqube_counts["BLOCKER"]>0 or sonarqube_counts["CRITICAL"]>0 else ("MAJOR" if sonarqube_counts["MAJOR"]>0 else ("MINOR" if sonarqube_counts["MINOR"]>0 else ("INFO" if sonarqube_counts["INFO"]>0 else "PASSED")))}">{sonarqube_icon}</span> <b>SonarQube:</b> {sonarqube_counts["BLOCKER"]} Blocker, {sonarqube_counts["CRITICAL"]} Critical, {sonarqube_counts["MAJOR"]} Major, {sonarqube_counts["MINOR"]} Minor, {sonarqube_counts["INFO"]} Info</div>')
    
    # Checkov Visual Summary
    if len(checkov_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Checkov:</b> No findings</div>')
    else:
        checkov_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in checkov_findings:
            sev = f['severity'].upper()
            if sev in checkov_counts:
                checkov_counts[sev] += 1
        checkov_icon = '✅' if sum(checkov_counts.values()) == 0 else ''
        if checkov_counts['CRITICAL'] > 0:
            checkov_icon = '🚨'
        elif checkov_counts['HIGH'] > 0:
            checkov_icon = '🚨'
        elif checkov_counts['MEDIUM'] > 0:
            checkov_icon = '⚠️'
        elif checkov_counts['LOW'] > 0 or checkov_counts['INFO'] > 0:
            checkov_icon = 'ℹ️'
        # Determine severity class
        if checkov_counts['CRITICAL'] > 0:
            checkov_sev = 'CRITICAL'
        elif checkov_counts['HIGH'] > 0:
            checkov_sev = 'HIGH'
        elif checkov_counts['MEDIUM'] > 0:
            checkov_sev = 'MEDIUM'
        elif checkov_counts['LOW'] > 0:
            checkov_sev = 'LOW'
        elif checkov_counts['INFO'] > 0:
            checkov_sev = 'INFO'
        else:
            checkov_sev = 'PASSED'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{checkov_sev}">{checkov_icon}</span> <b>Checkov:</b> {checkov_counts["CRITICAL"]} Critical, {checkov_counts["HIGH"]} High, {checkov_counts["MEDIUM"]} Medium, {checkov_counts["LOW"]} Low, {checkov_counts["INFO"]} Info</div>')
    
    # GitLeaks Visual Summary
    if len(gitleaks_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>GitLeaks:</b> No secrets detected</div>')
    else:
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-HIGH">🚨</span> <b>GitLeaks:</b> {len(gitleaks_findings)} secrets found</div>')
    
    # Detect-secrets Visual Summary
    if len(detect_secrets_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Detect-secrets:</b> No secrets detected</div>')
    else:
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-HIGH">🚨</span> <b>Detect-secrets:</b> {len(detect_secrets_findings)} secrets found</div>')
    
    # npm audit Visual Summary
    if len(npm_audit_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>npm audit:</b> No vulnerabilities</div>')
    else:
        npm_audit_counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0, "INFO": 0}
        for f in npm_audit_findings:
            sev = f['severity'].upper()
            if sev in npm_audit_counts:
                npm_audit_counts[sev] += 1
        npm_audit_icon = '✅' if sum(npm_audit_counts.values()) == 0 else ''
        if npm_audit_counts['CRITICAL'] > 0:
            npm_audit_icon = '🚨'
        elif npm_audit_counts['HIGH'] > 0:
            npm_audit_icon = '🚨'
        elif npm_audit_counts['MODERATE'] > 0:
            npm_audit_icon = '⚠️'
        elif npm_audit_counts['LOW'] > 0 or npm_audit_counts['INFO'] > 0:
            npm_audit_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if npm_audit_counts["CRITICAL"]>0 else ("HIGH" if npm_audit_counts["HIGH"]>0 else ("MODERATE" if npm_audit_counts["MODERATE"]>0 else ("LOW" if npm_audit_counts["LOW"]>0 else ("INFO" if npm_audit_counts["INFO"]>0 else "PASSED"))))}">{npm_audit_icon}</span> <b>npm audit:</b> {npm_audit_counts["CRITICAL"]} Critical, {npm_audit_counts["HIGH"]} High, {npm_audit_counts["MODERATE"]} Moderate, {npm_audit_counts["LOW"]} Low, {npm_audit_counts["INFO"]} Info</div>')
    
    # Wapiti Visual Summary
    if len(wapiti_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Wapiti:</b> No findings</div>')
    else:
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-MEDIUM">⚠️</span> <b>Wapiti:</b> {len(wapiti_findings)} vulnerabilities found</div>')
    
    # Nikto Visual Summary
    if len(nikto_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Nikto:</b> No findings</div>')
    else:
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-MEDIUM">⚠️</span> <b>Nikto:</b> {len(nikto_findings)} vulnerabilities found</div>')
    
    # Burp Suite Visual Summary
    if len(burp_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Burp Suite:</b> No findings</div>')
    else:
        burp_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in burp_findings:
            sev = f.get('severity', 'MEDIUM').upper()
            if sev in burp_counts:
                burp_counts[sev] += 1
        burp_icon = '✅' if sum(burp_counts.values()) == 0 else ''
        if burp_counts.get('CRITICAL', 0) > 0 or burp_counts['HIGH'] > 0:
            burp_icon = '🚨'
        elif burp_counts['MEDIUM'] > 0:
            burp_icon = '⚠️'
        elif burp_counts['LOW'] > 0:
            burp_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if burp_counts.get("CRITICAL", 0)>0 or burp_counts["HIGH"]>0 else ("MEDIUM" if burp_counts["MEDIUM"]>0 else ("LOW" if burp_counts["LOW"]>0 else "PASSED"))}">{burp_icon}</span> <b>Burp Suite:</b> {burp_counts.get("CRITICAL", 0)} Critical, {burp_counts["HIGH"]} High, {burp_counts["MEDIUM"]} Medium, {burp_counts["LOW"]} Low</div>')
    
    # Kube-hunter Visual Summary
    if len(kube_hunter_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Kube-hunter:</b> No findings</div>')
    else:
        kube_hunter_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in kube_hunter_findings:
            sev = f.get('severity', 'MEDIUM').upper()
            if sev in kube_hunter_counts:
                kube_hunter_counts[sev] += 1
        kube_hunter_icon = '✅' if sum(kube_hunter_counts.values()) == 0 else ''
        if kube_hunter_counts['HIGH'] > 0:
            kube_hunter_icon = '🚨'
        elif kube_hunter_counts['MEDIUM'] > 0:
            kube_hunter_icon = '⚠️'
        elif kube_hunter_counts['LOW'] > 0 or kube_hunter_counts['INFO'] > 0:
            kube_hunter_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if kube_hunter_counts["HIGH"]>0 else ("MEDIUM" if kube_hunter_counts["MEDIUM"]>0 else ("LOW" if kube_hunter_counts["LOW"]>0 else ("INFO" if kube_hunter_counts["INFO"]>0 else "PASSED")))}">{kube_hunter_icon}</span> <b>Kube-hunter:</b> {kube_hunter_counts["HIGH"]} High, {kube_hunter_counts["MEDIUM"]} Medium, {kube_hunter_counts["LOW"]} Low, {kube_hunter_counts["INFO"]} Info</div>')
    
    # Kube-bench Visual Summary
    if len(kube_bench_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Kube-bench:</b> No findings</div>')
    else:
        kube_bench_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0}
        for f in kube_bench_findings:
            state = f.get('state', 'WARN').upper()
            if state in kube_bench_counts:
                kube_bench_counts[state] += 1
        kube_bench_icon = '✅' if kube_bench_counts.get('FAIL', 0) == 0 and kube_bench_counts.get('WARN', 0) == 0 else ''
        if kube_bench_counts.get('FAIL', 0) > 0:
            kube_bench_icon = '🚨'
        elif kube_bench_counts.get('WARN', 0) > 0:
            kube_bench_icon = '⚠️'
        elif kube_bench_counts.get('PASS', 0) > 0:
            kube_bench_icon = '✅'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"FAIL" if kube_bench_counts.get("FAIL", 0)>0 else ("WARN" if kube_bench_counts.get("WARN", 0)>0 else ("PASS" if kube_bench_counts.get("PASS", 0)>0 else "INFO"))}">{kube_bench_icon}</span> <b>Kube-bench:</b> {kube_bench_counts.get("PASS", 0)} Pass, {kube_bench_counts.get("WARN", 0)} Warn, {kube_bench_counts.get("FAIL", 0)} Fail</div>')
    
    # Docker Bench Visual Summary
    if len(docker_bench_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Docker Bench:</b> No findings</div>')
    else:
        docker_bench_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0, "NOTE": 0}
        for f in docker_bench_findings:
            result = f.get('result', 'WARN').upper()
            if result in docker_bench_counts:
                docker_bench_counts[result] += 1
        docker_bench_icon = '✅' if docker_bench_counts.get('FAIL', 0) == 0 and docker_bench_counts.get('WARN', 0) == 0 else ''
        if docker_bench_counts.get('FAIL', 0) > 0:
            docker_bench_icon = '🚨'
        elif docker_bench_counts.get('WARN', 0) > 0:
            docker_bench_icon = '⚠️'
        elif docker_bench_counts.get('PASS', 0) > 0:
            docker_bench_icon = '✅'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"FAIL" if docker_bench_counts.get("FAIL", 0)>0 else ("WARN" if docker_bench_counts.get("WARN", 0)>0 else ("PASS" if docker_bench_counts.get("PASS", 0)>0 else "INFO"))}">{docker_bench_icon}</span> <b>Docker Bench:</b> {docker_bench_counts.get("PASS", 0)} Pass, {docker_bench_counts.get("WARN", 0)} Warn, {docker_bench_counts.get("FAIL", 0)} Fail</div>')
    
    # ESLint Visual Summary
    if len(eslint_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>ESLint:</b> No security issues</div>')
    else:
        eslint_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for f in eslint_findings:
            sev = f['severity']
            if sev == 2:
                eslint_counts['ERROR'] += 1
            elif sev == 1:
                eslint_counts['WARNING'] += 1
            elif sev == 0:
                eslint_counts['INFO'] += 1
        eslint_icon = '✅' if sum(eslint_counts.values()) == 0 else ''
        if eslint_counts['ERROR'] > 0:
            eslint_icon = '🚨'
        elif eslint_counts['WARNING'] > 0:
            eslint_icon = '⚠️'
        elif eslint_counts['INFO'] > 0:
            eslint_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"ERROR" if eslint_counts["ERROR"]>0 else ("WARNING" if eslint_counts["WARNING"]>0 else ("INFO" if eslint_counts["INFO"]>0 else "PASSED"))}">{eslint_icon}</span> <b>ESLint:</b> {eslint_counts["ERROR"]} Error, {eslint_counts["WARNING"]} Warning</div>')
    
    # Clair Visual Summary
    if len(clair_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Clair:</b> No vulnerabilities found</div>')
    else:
        clair_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for v in clair_findings:
            sev = v.get('Severity', '').upper()
            if sev in clair_counts:
                clair_counts[sev] += 1
        clair_icon = '✅' if sum(clair_counts.values()) == 0 else ''
        if clair_counts['CRITICAL'] > 0:
            clair_icon = '🚨'
        elif clair_counts['HIGH'] > 0:
            clair_icon = '🚨'
        elif clair_counts['MEDIUM'] > 0:
            clair_icon = '⚠️'
        elif clair_counts['LOW'] > 0 or clair_counts['INFO'] > 0:
            clair_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if clair_counts["CRITICAL"]>0 else ("HIGH" if clair_counts["HIGH"]>0 else ("MEDIUM" if clair_counts["MEDIUM"]>0 else ("LOW" if clair_counts["LOW"]>0 else ("INFO" if clair_counts["INFO"]>0 else "PASSED"))))}">{clair_icon}</span> <b>Clair:</b> {clair_counts["CRITICAL"]} Critical, {clair_counts["HIGH"]} High, {clair_counts["MEDIUM"]} Medium, {clair_counts["LOW"]} Low</div>')
    
    # Anchore Visual Summary
    if len(anchore_vulns) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Anchore:</b> No vulnerabilities found</div>')
    else:
        anchore_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for v in anchore_vulns:
            sev = v.get('Severity', '').upper()
            if sev in anchore_counts:
                anchore_counts[sev] += 1
        anchore_icon = '✅' if sum(anchore_counts.values()) == 0 else ''
        if anchore_counts['CRITICAL'] > 0:
            anchore_icon = '🚨'
        elif anchore_counts['HIGH'] > 0:
            anchore_icon = '🚨'
        elif anchore_counts['MEDIUM'] > 0:
            anchore_icon = '⚠️'
        elif anchore_counts['LOW'] > 0 or anchore_counts['INFO'] > 0:
            anchore_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"CRITICAL" if anchore_counts["CRITICAL"]>0 else ("HIGH" if anchore_counts["HIGH"]>0 else ("MEDIUM" if anchore_counts["MEDIUM"]>0 else ("LOW" if anchore_counts["LOW"]>0 else ("INFO" if anchore_counts["INFO"]>0 else "PASSED"))))}">{anchore_icon}</span> <b>Anchore:</b> {anchore_counts["CRITICAL"]} Critical, {anchore_counts["HIGH"]} High, {anchore_counts["MEDIUM"]} Medium, {anchore_counts["LOW"]} Low</div>')
    
    # Brakeman Visual Summary
    if len(brakeman_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Brakeman:</b> No vulnerabilities found</div>')
    else:
        brakeman_counts = {"HIGH": 0, "MEDIUM": 0, "WEAK": 0}
        for f in brakeman_findings:
            conf = f.get('confidence', '').upper()
            if conf in brakeman_counts:
                brakeman_counts[conf] += 1
        brakeman_icon = '✅' if sum(brakeman_counts.values()) == 0 else ''
        if brakeman_counts['HIGH'] > 0 or any(c in ('HIGH', 'CERTAIN') for c in [f.get('confidence', '').upper() for f in brakeman_findings]):
            brakeman_icon = '🚨'
        elif brakeman_counts['MEDIUM'] > 0:
            brakeman_icon = '⚠️'
        elif brakeman_counts['WEAK'] > 0:
            brakeman_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if brakeman_counts["HIGH"]>0 else ("MEDIUM" if brakeman_counts["MEDIUM"]>0 else "PASSED")}">{brakeman_icon}</span> <b>Brakeman:</b> {len(brakeman_findings)} Ruby security issues</div>')
    
    # Bandit Visual Summary
    if len(bandit_findings) == 0:
        html_parts.append('<div class="tool-summary"><span class="icon sev-PASSED">✅</span> <b>Bandit:</b> No Python vulnerabilities found</div>')
    else:
        bandit_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in bandit_findings:
            sev = f.get('severity', '').upper()
            if sev in bandit_counts:
                bandit_counts[sev] += 1
        bandit_icon = '✅' if sum(bandit_counts.values()) == 0 else ''
        if bandit_counts['HIGH'] > 0:
            bandit_icon = '🚨'
        elif bandit_counts['MEDIUM'] > 0:
            bandit_icon = '⚠️'
        elif bandit_counts['LOW'] > 0:
            bandit_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if bandit_counts["HIGH"]>0 else ("MEDIUM" if bandit_counts["MEDIUM"]>0 else ("LOW" if bandit_counts["LOW"]>0 else "PASSED"))}">{bandit_icon}</span> <b>Bandit:</b> {bandit_counts["HIGH"]} High, {bandit_counts["MEDIUM"]} Medium, {bandit_counts["LOW"]} Low</div>')
    
    # Android Manifest Visual Summary
    if android_findings:
        android_icon = '✅' if android_findings.get('total_issues', 0) == 0 else ''
        if android_findings.get('high', 0) > 0:
            android_icon = '🚨'
        elif android_findings.get('medium', 0) > 0:
            android_icon = '⚠️'
        elif android_findings.get('info', 0) > 0:
            android_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if android_findings.get("high", 0)>0 else ("MEDIUM" if android_findings.get("medium", 0)>0 else ("INFO" if android_findings.get("info", 0)>0 else "PASSED"))}">{android_icon}</span> <b>Android Manifest:</b> {android_findings.get("high", 0)} High, {android_findings.get("medium", 0)} Medium, {android_findings.get("info", 0)} Info</div>')
    
    # iOS Plist Visual Summary
    if ios_findings:
        ios_icon = '✅' if ios_findings.get('total_issues', 0) == 0 else ''
        if ios_findings.get('high', 0) > 0:
            ios_icon = '🚨'
        elif ios_findings.get('medium', 0) > 0:
            ios_icon = '⚠️'
        elif ios_findings.get('info', 0) > 0:
            ios_icon = 'ℹ️'
        html_parts.append(f'<div class="tool-summary"><span class="icon sev-{"HIGH" if ios_findings.get("high", 0)>0 else ("MEDIUM" if ios_findings.get("medium", 0)>0 else ("INFO" if ios_findings.get("info", 0)>0 else "PASSED"))}">{ios_icon}</span> <b>iOS Plist:</b> {ios_findings.get("high", 0)} High, {ios_findings.get("medium", 0)} Medium, {ios_findings.get("info", 0)} Info</div>')
    
    return "".join(html_parts)

def generate_overall_summary_and_links_section(zap_alerts, semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_dc_vulns, safety_findings, snyk_findings, sonarqube_findings, checkov_findings, trufflehog_findings, gitleaks_findings, detect_secrets_findings, npm_audit_findings, wapiti_findings, nikto_findings, burp_findings, kube_hunter_findings, kube_bench_findings, docker_bench_findings, eslint_findings, clair_findings, anchore_vulns, brakeman_findings, bandit_findings, results_dir, path_module, os_module, android_findings=None, ios_findings=None):
    html_parts = []
    html_parts.append('<h2>Overall Summary</h2>\n')
    html_parts.append('<ul>')
    html_parts.append(f'<li>ZAP Alerts: {zap_alerts["High"]} High, {zap_alerts["Medium"]} Medium, {zap_alerts["Low"]} Low, {zap_alerts["Informational"]} Informational</li>')
    html_parts.append(f'<li>Semgrep Findings: {len(semgrep_findings)}</li>')
    html_parts.append(f'<li>Trivy Vulnerabilities: {len(trivy_vulns)}</li>')
    html_parts.append(f'<li>CodeQL Findings: {len(codeql_findings)}</li>')
    html_parts.append(f'<li>Nuclei Findings: {len(nuclei_findings)}</li>')
    html_parts.append(f'<li>OWASP Dependency Check Vulnerabilities: {len(owasp_dc_vulns)}</li>')
    html_parts.append(f'<li>Safety Vulnerabilities: {len(safety_findings)}</li>')
    html_parts.append(f'<li>Snyk Vulnerabilities: {len(snyk_findings)}</li>')
    html_parts.append(f'<li>SonarQube Code Quality Issues: {len(sonarqube_findings)}</li>')
    html_parts.append(f'<li>Checkov Terraform Security Issues: {len(checkov_findings)}</li>')
    html_parts.append(f'<li>TruffleHog Secret Detection: {len(trufflehog_findings)}</li>')
    html_parts.append(f'<li>GitLeaks Secret Detection: {len(gitleaks_findings)}</li>')
    html_parts.append(f'<li>Detect-secrets Secret Detection: {len(detect_secrets_findings)}</li>')
    html_parts.append(f'<li>npm audit Vulnerabilities: {len(npm_audit_findings)}</li>')
    html_parts.append(f'<li>Wapiti Web Vulnerability Scan: {len(wapiti_findings)}</li>')
    html_parts.append(f'<li>Nikto Web Server Scan: {len(nikto_findings)}</li>')
    html_parts.append(f'<li>Burp Suite Web Application Security Scan: {len(burp_findings)}</li>')
    html_parts.append(f'<li>Kube-hunter Kubernetes Security Scan: {len(kube_hunter_findings)}</li>')
    html_parts.append(f'<li>Kube-bench Kubernetes Compliance Scan: {len(kube_bench_findings)}</li>')
    html_parts.append(f'<li>Docker Bench Docker Daemon Compliance Scan: {len(docker_bench_findings)}</li>')
    html_parts.append(f'<li>ESLint JavaScript/TypeScript Security Scan: {len(eslint_findings)}</li>')
    html_parts.append(f'<li>Clair Container Image Vulnerability Scan: {len(clair_findings)}</li>')
    html_parts.append(f'<li>Anchore Container Image Security Scan: {len(anchore_vulns)}</li>')
    html_parts.append(f'<li>Brakeman Ruby on Rails Security Scan: {len(brakeman_findings)}</li>')
    html_parts.append(f'<li>Bandit Python Code Security Scan: {len(bandit_findings)}</li>')
    if android_findings:
        html_parts.append(f'<li>Android Manifest Security Scan: {android_findings.get("total_issues", 0)} issues</li>')
    if ios_findings:
        html_parts.append(f'<li>iOS Plist Security Scan: {ios_findings.get("total_issues", 0)} issues</li>')
    html_parts.append('</ul>')
    html_parts.append('<h2>Links to Raw Reports</h2>\n<ul>')
    for name in ['zap-report.html', 'zap-report.xml', 'semgrep.json', 'trivy.json', 'codeql.json', 'nuclei.json', 'owasp-dependency-check.json', 'owasp-dependency-check.html', 'owasp-dependency-check.xml', 'codeql.sarif', 'semgrep.txt', 'trivy.txt', 'codeql.txt', 'nuclei.txt', 'safety.json', 'safety.txt', 'snyk.json', 'snyk.txt', 'sonarqube.json', 'sonarqube.txt', 'checkov.json', 'checkov.txt', 'trufflehog.json', 'trufflehog.txt', 'gitleaks.json', 'gitleaks.txt', 'npm-audit.json', 'npm-audit.txt', 'wapiti.json', 'wapiti.txt', 'nikto.json', 'nikto.txt', 'kube-hunter.json', 'kube-hunter.txt', 'kube-bench.json', 'kube-bench.txt', 'docker-bench.json', 'docker-bench.txt', 'eslint.json', 'eslint.txt', 'clair.json', 'clair.txt', 'anchore.json', 'anchore.txt', 'brakeman.json', 'brakeman.txt', 'bandit.json', 'bandit.txt', 'android-manifest.json', 'android-manifest.txt', 'ios-plist.json', 'ios-plist.txt']:
        # Path_module and os_module are used here for consistency, though os_module.path.join is the key part
        path = os_module.path.join(results_dir, name)
        if Path_module(path).exists():
            html_parts.append(f'<li><a href="{name}">{name}</a></li>')
    html_parts.append('</ul>')
    return "".join(html_parts) 