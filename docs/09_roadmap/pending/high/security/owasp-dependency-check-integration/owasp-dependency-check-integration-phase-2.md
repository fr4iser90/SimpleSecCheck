# OWASP Dependency Check Integration – Phase 2: Core Implementation

## Overview
Create the core OWASP Dependency Check execution script and result processor following SimpleSecCheck patterns.

## Objectives
- [ ] Create tool execution script following existing patterns
- [ ] Create result processor for JSON parsing and HTML generation
- [ ] Implement LLM integration for explanations
- [ ] Test core functionality with sample projects

## Deliverables
- File: `scripts/tools/run_owasp_dependency_check.sh` - Tool execution script
- File: `scripts/owasp_dependency_check_processor.py` - Result processor
- Test: Core functionality verification
- Test: JSON parsing and HTML generation

## Dependencies
- Requires: Phase 1 completion (OWASP Dependency Check installation)
- Blocks: Phase 3 start

## Estimated Time
2 hours

## Detailed Tasks

### Task 2.1: Tool Execution Script (1 hour)
- [ ] **2.1.1** Create `run_owasp_dependency_check.sh` following Trivy pattern
- [ ] **2.1.2** Implement environment variable handling
- [ ] **2.1.3** Add JSON and HTML output generation
- [ ] **2.1.4** Implement error handling and logging

### Task 2.2: Result Processor (1 hour)
- [ ] **2.2.1** Create `owasp_dependency_check_processor.py` following Trivy pattern
- [ ] **2.2.2** Implement JSON parsing for vulnerability data
- [ ] **2.2.3** Add HTML section generation
- [ ] **2.2.4** Integrate LLM explanations for findings

## Technical Implementation Details

### Tool Execution Script Pattern
```bash
#!/bin/bash
# Individual OWASP Dependency Check Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
OWASP_CONFIG_PATH="${OWASP_CONFIG_PATH:-/SimpleSecCheck/owasp-dependency-check/config.yaml}"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_owasp_dependency_check.sh] Initializing OWASP Dependency Check scan..." | tee -a "$LOG_FILE"

if command -v dependency-check &>/dev/null; then
  echo "[run_owasp_dependency_check.sh][OWASP] Running dependency scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  OWASP_JSON="$RESULTS_DIR/owasp-dependency-check.json"
  OWASP_HTML="$RESULTS_DIR/owasp-dependency-check.html"
  
  # Run dependency check with JSON and HTML output
  dependency-check --project "SimpleSecCheck Scan" \
                   --scan "$TARGET_PATH" \
                   --format JSON \
                   --out "$RESULTS_DIR" \
                   --config "$OWASP_CONFIG_PATH" \
                   2>>"$LOG_FILE" || {
    echo "[run_owasp_dependency_check.sh][OWASP] Scan failed." >> "$LOG_FILE"
    exit 1
  }
  
  # Move generated files to expected locations
  mv "$RESULTS_DIR/dependency-check-report.json" "$OWASP_JSON" 2>/dev/null || true
  mv "$RESULTS_DIR/dependency-check-report.html" "$OWASP_HTML" 2>/dev/null || true
  
  if [ -f "$OWASP_JSON" ] || [ -f "$OWASP_HTML" ]; then
    echo "[run_owasp_dependency_check.sh][OWASP] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$OWASP_JSON" ] && echo "  - $OWASP_JSON" | tee -a "$LOG_FILE"
    [ -f "$OWASP_HTML" ] && echo "  - $OWASP_HTML" | tee -a "$LOG_FILE"
    echo "[OWASP Dependency Check] Dependency scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_owasp_dependency_check.sh][OWASP][ERROR] No OWASP Dependency Check report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_owasp_dependency_check.sh][ERROR] dependency-check not found, skipping dependency scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### Result Processor Pattern
```python
#!/usr/bin/env python3
import sys
import json
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[owasp_dependency_check_processor] {msg}", file=sys.stderr)

def owasp_dependency_check_summary(owasp_json):
    vulnerabilities = []
    if owasp_json and 'dependencies' in owasp_json:
        for dep in owasp_json['dependencies']:
            for vuln in dep.get('vulnerabilities', []):
                vuln_data = {
                    'name': dep.get('fileName', ''),
                    'severity': vuln.get('severity', ''),
                    'cve': vuln.get('name', ''),
                    'description': vuln.get('description', ''),
                    'cvss_score': vuln.get('cvssScore', ''),
                    'cvss_vector': vuln.get('cvssVector', '')
                }
                
                # Get AI explanation
                prompt = f"Explain this dependency vulnerability: {vuln_data['description']} in {vuln_data['name']} with CVSS score {vuln_data['cvss_score']}"
                try:
                    if llm_client:
                        vuln_data['ai_explanation'] = llm_client.query(prompt)
                    else:
                        vuln_data['ai_explanation'] = "LLM client not available."
                except Exception as e:
                    debug(f"LLM query failed for OWASP finding: {e}")
                    vuln_data['ai_explanation'] = "Error fetching AI explanation."
                
                vulnerabilities.append(vuln_data)
    else:
        debug("No OWASP Dependency Check results found in JSON.")
    
    return vulnerabilities

def generate_owasp_dependency_check_html_section(owasp_vulns):
    html_parts = []
    html_parts.append('<h2>OWASP Dependency Check</h2>')
    if owasp_vulns:
        html_parts.append('<table><tr><th>Dependency</th><th>Severity</th><th>CVE</th><th>CVSS Score</th><th>Description</th><th>AI Explanation</th></tr>')
        for v in owasp_vulns:
            sev = v['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            # HTML escaping
            name_escaped = html.escape(str(v["name"]))
            sev_escaped = html.escape(str(sev))
            cve_escaped = html.escape(str(v["cve"]))
            score_escaped = html.escape(str(v["cvss_score"]))
            desc_escaped = html.escape(str(v["description"]))
            ai_exp_escaped = html.escape(str(v.get("ai_explanation", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{cve_escaped}</td><td>{score_escaped}</td><td>{desc_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No dependency vulnerabilities found.</div>')
    return "".join(html_parts)
```

## Success Criteria
- [ ] Tool script executes OWASP Dependency Check successfully
- [ ] JSON reports are generated and parsed correctly
- [ ] HTML sections are generated following existing patterns
- [ ] LLM integration works for vulnerability explanations
- [ ] Error handling works properly
- [ ] Logging follows existing patterns

## Testing Checklist
- [ ] Test script with sample project
- [ ] Verify JSON output format
- [ ] Test HTML generation
- [ ] Verify LLM integration
- [ ] Test error scenarios
- [ ] Check logging output
