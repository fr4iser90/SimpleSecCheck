#!/usr/bin/env python3
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import os

# It's good practice to have a common debug utility or pass it as an argument
# For now, defining it here for simplicity as it was in the original script context
def debug(msg):
    print(f"[zap_processor] {msg}", file=sys.stderr)

def zap_summary(zap_html_path, zap_xml_path):
    # Try XML first - return detailed alerts, not just counts
    if zap_xml_path and Path(zap_xml_path).exists():
        try:
            tree = ET.parse(zap_xml_path)
            root = tree.getroot()
            alerts = root.findall('.//alertitem')
            detailed_alerts = []
            summary = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
            
            for alert in alerts:
                alert_data = {
                    'alert': alert.findtext('alert', 'Unknown'),
                    'riskdesc': alert.findtext('riskdesc', 'Unknown'),
                    'desc': alert.findtext('desc', 'No description'),
                    'solution': alert.findtext('solution', 'No solution provided'),
                    'count': alert.findtext('count', '0'),
                    'instances': []
                }
                
                # Extract instances
                for instance in alert.findall('instances/instance'):
                    instance_data = {
                        'uri': instance.findtext('uri', 'Unknown'),
                        'method': instance.findtext('method', 'Unknown'),
                        'param': instance.findtext('param', ''),
                        'evidence': instance.findtext('evidence', '')
                    }
                    alert_data['instances'].append(instance_data)
                
                detailed_alerts.append(alert_data)
                
                # Count by risk level
                riskdesc = alert_data['riskdesc']
                if riskdesc.startswith('High'):
                    summary["High"] += 1
                elif riskdesc.startswith('Medium'):
                    summary["Medium"] += 1
                elif riskdesc.startswith('Low'):
                    summary["Low"] += 1
                elif riskdesc.startswith('Informational'):
                    summary["Informational"] += 1
            
            return {"summary": summary, "alerts": detailed_alerts}
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
                return {"summary": summary, "alerts": []}
        except Exception as e:
            debug(f"Error parsing ZAP HTML: {e}")
    
    # Fallback: all zeros
    return {"summary": {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}, "alerts": []}

def generate_zap_html_section(zap_data, zap_html_path, Path_module, os_module):
    html_parts = []
    html_parts.append('<h2>ZAP Web Vulnerability Scan</h2>')
    
    # Handle both old format (just counts) and new format (with details)
    if isinstance(zap_data, dict) and 'summary' in zap_data:
        # New format with details
        summary = zap_data['summary']
        alerts = zap_data['alerts']
        
        # Show summary table
        html_parts.append('<table><tr><th>Risk Level</th><th>Number of Alerts</th></tr>')
        for risk, count in summary.items():
            icon = ''
            sev_class = risk.upper()
            if risk == 'High': icon = '🚨'
            elif risk == 'Medium': icon = '⚠️'
            elif risk == 'Low': icon = 'ℹ️'
            elif risk == 'Informational': icon = 'ℹ️'
            html_parts.append(f'<tr class="row-{sev_class}"><td class="severity-{sev_class}">{icon} {risk}</td><td>{count}</td></tr>')
        html_parts.append('</table>')
        
        # Show detailed findings
        if alerts:
            html_parts.append('<h3>Detailed Findings</h3>')
            for alert in alerts:
                risk_level = alert['riskdesc'].split()[0] if alert['riskdesc'] else 'Unknown'
                css_class = risk_level.lower()
                
                html_parts.append(f'''
                <div class="alert-detail {css_class}">
                    <h4>{alert['alert']}</h4>
                    <div class="alert-meta">
                        <span class="risk-badge {css_class}">{alert['riskdesc']}</span>
                        <span class="alert-count">Count: {alert['count']}</span>
                    </div>
                    <div class="alert-description">
                        <p><strong>Description:</strong></p>
                        <p>{alert['desc']}</p>
                    </div>
                    <div class="alert-solution">
                        <p><strong>Solution:</strong></p>
                        <p>{alert['solution']}</p>
                    </div>
                </div>
                ''')
        elif sum(summary.values()) == 0:
            html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>')
    else:
        # Old format - just counts
        if zap_data:
            html_parts.append('<table><tr><th>Risk Level</th><th>Number of Alerts</th></tr>')
            for risk, count in zap_data.items():
                icon = ''
                sev_class = risk.upper()
                if risk == 'High': icon = '🚨'
                elif risk == 'Medium': icon = '⚠️'
                elif risk == 'Low': icon = 'ℹ️'
                elif risk == 'Informational': icon = 'ℹ️'
                html_parts.append(f'<tr class="row-{sev_class}"><td class="severity-{sev_class}">{icon} {risk}</td><td>{count}</td></tr>')
            html_parts.append('</table>')
            if sum(zap_data.values()) == 0:
                html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>')
        else:
            html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web vulnerabilities found.</div>')
    
    # Path_module and os_module are used here as direct replacements for Path and os.path
    if Path_module(zap_html_path).exists():
        html_parts.append(f'<p>See full ZAP report: <a href="zap-report.xml.html">zap-report.xml.html</a></p>')
    elif Path_module(os_module.path.join(os_module.environ.get('RESULTS_DIR', '/SimpleSecCheck/results'), "zap-report.html")).exists():
        html_parts.append(f'<p>See full ZAP report: <a href="zap-report.html">zap-report.html</a></p>')
    return "".join(html_parts) 