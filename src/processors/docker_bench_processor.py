#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[docker_bench_processor] {msg}", file=sys.stderr)

def docker_bench_summary(docker_bench_json):
    findings = []
    if docker_bench_json and isinstance(docker_bench_json, dict):
        # Parse Docker Bench JSON output
        checks_records = docker_bench_json.get('tests', [])
        for check_group in checks_records:
            group_name = check_group.get('group', 'Docker Compliance')
            group_summary = check_group.get('summary', {})
            
            # Extract check results
            for test in check_group.get('checks', []):
                finding = {
                    'test': test.get('test', ''),
                    'result': test.get('result', ''),
                    'group': group_name,
                    'description': test.get('test', ''),
                    'remediation': ''
                }
                findings.append(finding)
    elif docker_bench_json and isinstance(docker_bench_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(docker_bench_json)
            if isinstance(data, dict):
                checks_records = data.get('tests', [])
                for check_group in checks_records:
                    group_name = check_group.get('group', 'Docker Compliance')
                    
                    # Extract check results
                    for test in check_group.get('checks', []):
                        finding = {
                            'test': test.get('test', ''),
                            'result': test.get('result', ''),
                            'group': group_name,
                            'description': test.get('test', ''),
                            'remediation': ''
                        }
                        findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse Docker Bench JSON as string.")
    else:
        debug("No Docker Bench results found in JSON.")
    return findings

def generate_docker_bench_html_section(docker_bench_findings):
    html_parts = []
    html_parts.append('<h2>Docker Bench Docker Daemon Compliance Scan</h2>')
    if docker_bench_findings:
        html_parts.append('<table><tr><th>Check</th><th>Result</th><th>Group</th></tr>')
        for finding in docker_bench_findings:
            test_escaped = html.escape(str(finding.get('test', '')))
            result_escaped = html.escape(str(finding.get('result', '')))
            group_escaped = html.escape(str(finding.get('group', '')))
            
            # Color-code result
            result_class = "sev-MEDIUM"
            icon = '✅'
            if finding.get('result', '').upper() == 'PASS':
                result_class = "sev-PASSED"
                icon = '✅'
            elif finding.get('result', '').upper() == 'WARN':
                result_class = "sev-MEDIUM"
                icon = '⚠️'
            elif finding.get('result', '').upper() == 'INFO':
                result_class = "sev-LOW"
                icon = 'ℹ️'
            elif finding.get('result', '').upper() == 'NOTE':
                result_class = "sev-LOW"
                icon = 'ℹ️'
            
            html_parts.append(f'<tr class="row-{finding.get("result", "WARN").upper()}"><td>{test_escaped}</td><td class="{result_class}">{icon} {result_escaped}</td><td>{group_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Docker compliance issues found.</div>')
    return "".join(html_parts)

