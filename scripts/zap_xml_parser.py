#!/usr/bin/env python3
"""
ZAP XML Report Parser
Converts ZAP XML reports to readable HTML format
"""

import xml.etree.ElementTree as ET
import sys
import json
from datetime import datetime

def parse_zap_xml(xml_file):
    """Parse ZAP XML report and return structured data"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Extract site information
        site_info = {}
        for site in root.findall('site'):
            site_info = {
                'name': site.get('name', 'Unknown'),
                'host': site.get('host', 'Unknown'),
                'port': site.get('port', 'Unknown'),
                'ssl': site.get('ssl', 'false')
            }
            break
        
        # Extract alerts
        alerts = []
        for alert in root.findall('.//alertitem'):
            alert_data = {
                'pluginid': alert.find('pluginid').text if alert.find('pluginid') is not None else 'Unknown',
                'alert': alert.find('alert').text if alert.find('alert') is not None else 'Unknown',
                'riskcode': alert.find('riskcode').text if alert.find('riskcode') is not None else '0',
                'riskdesc': alert.find('riskdesc').text if alert.find('riskdesc') is not None else 'Unknown',
                'desc': alert.find('desc').text if alert.find('desc') is not None else 'No description',
                'solution': alert.find('solution').text if alert.find('solution') is not None else 'No solution provided',
                'count': alert.find('count').text if alert.find('count') is not None else '0',
                'instances': []
            }
            
            # Extract instances
            for instance in alert.findall('instances/instance'):
                instance_data = {
                    'uri': instance.find('uri').text if instance.find('uri') is not None else 'Unknown',
                    'method': instance.find('method').text if instance.find('method') is not None else 'Unknown',
                    'param': instance.find('param').text if instance.find('param') is not None else '',
                    'evidence': instance.find('evidence').text if instance.find('evidence') is not None else ''
                }
                alert_data['instances'].append(instance_data)
            
            alerts.append(alert_data)
        
        return {
            'site': site_info,
            'alerts': alerts,
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        return None

def generate_html_report(data):
    """Generate HTML report from parsed data"""
    if not data:
        return "<html><body><h1>Error parsing ZAP report</h1></body></html>"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ZAP Security Report - {data['site']['name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .alert {{ margin: 20px 0; padding: 15px; border-left: 5px solid #ccc; }}
        .high {{ border-left-color: #d32f2f; background: #ffebee; }}
        .medium {{ border-left-color: #f57c00; background: #fff3e0; }}
        .low {{ border-left-color: #1976d2; background: #e3f2fd; }}
        .info {{ border-left-color: #388e3c; background: #e8f5e8; }}
        .risk-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }}
        .risk-high {{ background: #d32f2f; }}
        .risk-medium {{ background: #f57c00; }}
        .risk-low {{ background: #1976d2; }}
        .risk-info {{ background: #388e3c; }}
        .instance {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        .code {{ background: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ ZAP Security Report</h1>
        <p><strong>Target:</strong> {data['site']['name']} ({data['site']['host']}:{data['site']['port']})</p>
        <p><strong>Scan Date:</strong> {data['scan_date']}</p>
        <p><strong>SSL:</strong> {'Yes' if data['site']['ssl'] == 'true' else 'No'}</p>
    </div>
    
    <h2>📊 Summary</h2>
    <p>Total Alerts: {len(data['alerts'])}</p>
"""

    # Count alerts by risk level
    risk_counts = {'High': 0, 'Medium': 0, 'Low': 0, 'Informational': 0}
    for alert in data['alerts']:
        risk_level = alert['riskdesc'].split()[0] if alert['riskdesc'] else 'Informational'
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    html += f"""
    <ul>
        <li>🚨 High: {risk_counts['High']}</li>
        <li>⚠️ Medium: {risk_counts['Medium']}</li>
        <li>ℹ️ Low: {risk_counts['Low']}</li>
        <li>ℹ️ Informational: {risk_counts['Informational']}</li>
    </ul>
    
    <h2>🔍 Detailed Findings</h2>
"""

    # Sort alerts by risk level
    risk_order = {'High': 0, 'Medium': 1, 'Low': 2, 'Informational': 3}
    sorted_alerts = sorted(data['alerts'], key=lambda x: risk_order.get(x['riskdesc'].split()[0] if x['riskdesc'] else 'Informational', 4))
    
    for alert in sorted_alerts:
        risk_level = alert['riskdesc'].split()[0] if alert['riskdesc'] else 'Informational'
        css_class = risk_level.lower()
        
        html += f"""
    <div class="alert {css_class}">
        <h3>{alert['alert']}</h3>
        <span class="risk-badge risk-{css_class}">{alert['riskdesc']}</span>
        <p><strong>Plugin ID:</strong> {alert['pluginid']}</p>
        <p><strong>Count:</strong> {alert['count']}</p>
        
        <h4>Description:</h4>
        <div class="code">{alert['desc']}</div>
        
        <h4>Solution:</h4>
        <div class="code">{alert['solution']}</div>
        
        <h4>Instances ({len(alert['instances'])}):</h4>
"""
        
        for i, instance in enumerate(alert['instances'][:5]):  # Limit to first 5 instances
            html += f"""
        <div class="instance">
            <p><strong>Instance {i+1}:</strong></p>
            <p><strong>URI:</strong> {instance['uri']}</p>
            <p><strong>Method:</strong> {instance['method']}</p>
"""
            if instance['param']:
                html += f"<p><strong>Parameter:</strong> {instance['param']}</p>"
            if instance['evidence']:
                html += f"<p><strong>Evidence:</strong> {instance['evidence']}</p>"
            html += "</div>"
        
        if len(alert['instances']) > 5:
            html += f"<p><em>... and {len(alert['instances']) - 5} more instances</em></p>"
        
        html += "</div>"
    
    html += """
</body>
</html>
"""
    return html

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 zap_xml_parser.py <zap-report.xml>", file=sys.stderr)
        sys.exit(1)
    
    xml_file = sys.argv[1]
    data = parse_zap_xml(xml_file)
    
    if data:
        html_report = generate_html_report(data)
        print(html_report)
    else:
        print("Failed to parse ZAP XML report", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
