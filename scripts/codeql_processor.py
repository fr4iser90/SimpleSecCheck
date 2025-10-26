#!/usr/bin/env python3
import sys
import json
import html

def debug(msg):
    print(f"[codeql_processor] {msg}", file=sys.stderr)

def codeql_summary(codeql_json):
    findings = []
    if codeql_json:
        try:
            # Handle different CodeQL output formats
            if isinstance(codeql_json, dict):
                # SARIF format
                if 'runs' in codeql_json:
                    for run in codeql_json['runs']:
                        if 'results' in run:
                            for result in run['results']:
                                finding = {
                                    'rule_id': result.get('ruleId', ''),
                                    'level': result.get('level', ''),
                                    'message': result.get('message', {}).get('text', ''),
                                    'locations': result.get('locations', []),
                                    'severity': result.get('level', 'note').upper()
                                }
                                
                                # Extract file path and line number from locations
                                if finding['locations']:
                                    location = finding['locations'][0]
                                    if 'physicalLocation' in location:
                                        phy_loc = location['physicalLocation']
                                        finding['path'] = phy_loc.get('artifactLocation', {}).get('uri', '')
                                        if 'region' in phy_loc:
                                            finding['start'] = phy_loc['region'].get('startLine', '')
                                else:
                                    finding['path'] = ''
                                    finding['start'] = ''
                                
                                findings.append(finding)
                
                # Direct results format
                elif 'results' in codeql_json:
                    for result in codeql_json['results']:
                        finding = {
                            'rule_id': result.get('ruleId', ''),
                            'level': result.get('level', ''),
                            'message': result.get('message', ''),
                            'path': result.get('path', ''),
                            'start': result.get('start', {}).get('line', ''),
                            'severity': result.get('level', 'note').upper()
                        }
                        findings.append(finding)
            
            # Handle list format
            elif isinstance(codeql_json, list):
                for result in codeql_json:
                    finding = {
                        'rule_id': result.get('ruleId', ''),
                        'level': result.get('level', ''),
                        'message': result.get('message', ''),
                        'path': result.get('path', ''),
                        'start': result.get('start', {}).get('line', '') if isinstance(result.get('start'), dict) else result.get('start', ''),
                        'severity': result.get('level', 'note').upper()
                    }
                    findings.append(finding)
        
        except Exception as e:
            debug(f"Error parsing CodeQL JSON: {e}")
            return []
    else:
        debug("No CodeQL results found in JSON.")
    
    return findings

def generate_codeql_html_section(codeql_findings):
    html_parts = []
    html_parts.append('<h2>CodeQL Static Analysis</h2>')
    if codeql_findings:
        html_parts.append('<table><tr><th>Rule</th><th>File</th><th>Line</th><th>Message</th><th>Severity</th></tr>')
        for finding in codeql_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'ERROR': icon = '🚨'
            elif sev == 'WARNING': icon = '⚠️'
            elif sev == 'NOTE': icon = 'ℹ️'
            elif sev == 'INFO': icon = 'ℹ️'
            
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            path_escaped = html.escape(str(finding.get("path", "")))
            start_escaped = html.escape(str(finding.get("start", "")))
            message_escaped = html.escape(str(finding.get("message", "")))
            sev_escaped = html.escape(str(sev))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{rule_id_escaped}</td><td>{path_escaped}</td><td>{start_escaped}</td><td>{message_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No CodeQL findings detected.</div>')
    return "".join(html_parts)
