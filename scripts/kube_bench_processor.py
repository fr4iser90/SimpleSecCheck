#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[kube_bench_processor] {msg}", file=sys.stderr)

def kube_bench_summary(kube_bench_json):
    findings = []
    if kube_bench_json and isinstance(kube_bench_json, dict):
        # Parse Kube-bench JSON output
        checks_records = kube_bench_json.get('tests', [])
        for check_group in checks_records:
            group_name = check_group.get('group', '')
            group_summary = check_group.get('summary', {})
            
            # Extract check results
            for test in check_group.get('checks', []):
                finding = {
                    'id': test.get('id', ''),
                    'description': test.get('description', ''),
                    'state': test.get('state', ''),
                    'group': group_name,
                    'remediation': test.get('remediation', '')
                }
                findings.append(finding)
    elif kube_bench_json and isinstance(kube_bench_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(kube_bench_json)
            if isinstance(data, dict):
                checks_records = data.get('tests', [])
                for check_group in checks_records:
                    group_name = check_group.get('group', '')
                    
                    # Extract check results
                    for test in check_group.get('checks', []):
                        finding = {
                            'id': test.get('id', ''),
                            'description': test.get('description', ''),
                            'state': test.get('state', ''),
                            'group': group_name,
                            'remediation': test.get('remediation', '')
                        }
                        findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse Kube-bench JSON as string.")
    else:
        debug("No Kube-bench results found in JSON.")
    return findings

def generate_kube_bench_html_section(kube_bench_findings):
    html_parts = []
    html_parts.append('<h2>Kube-bench Kubernetes Compliance Scan</h2>')
    if kube_bench_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>State</th><th>Group</th><th>Description</th><th>Remediation</th></tr>')
        for finding in kube_bench_findings:
            check_id_escaped = html.escape(str(finding.get('id', '')))
            state_escaped = html.escape(str(finding.get('state', '')))
            group_escaped = html.escape(str(finding.get('group', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            remediation_escaped = html.escape(str(finding.get('remediation', '')))
            
            # Color-code state
            state_class = "sev-MEDIUM"
            icon = '⚠️'
            if finding.get('state', '').upper() == 'PASS':
                state_class = "sev-PASSED"
                icon = '✅'
            elif finding.get('state', '').upper() == 'WARN':
                state_class = "sev-MEDIUM"
                icon = '⚠️'
            elif finding.get('state', '').upper() == 'FAIL':
                state_class = "sev-HIGH"
                icon = '🚨'
            
            html_parts.append(f'<tr class="row-{finding.get("state", "WARN").upper()}"><td>{check_id_escaped}</td><td class="{state_class}">{icon} {state_escaped}</td><td>{group_escaped}</td><td>{description_escaped}</td><td>{remediation_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Kubernetes compliance issues found.</div>')
    return "".join(html_parts)

