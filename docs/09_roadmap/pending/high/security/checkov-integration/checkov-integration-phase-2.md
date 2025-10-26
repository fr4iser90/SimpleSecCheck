# Checkov Integration – Phase 2: Core Implementation

## Overview
Create the Checkov execution script and processor for parsing results and generating HTML reports. This phase implements the core functionality for running Checkov scans and processing results.

## Objectives
- [ ] Create scripts/tools/run_checkov.sh execution script
- [ ] Create scripts/checkov_processor.py result processor
- [ ] Implement JSON and text report generation
- [ ] Integrate with LLM explanations
- [ ] Implement error handling and logging

## Deliverables
- File: `scripts/tools/run_checkov.sh` - Checkov execution script
- File: `scripts/checkov_processor.py` - Checkov result processor

## Dependencies
- Requires: Phase 1 completion (Foundation Setup)
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov script executes scans correctly
- [ ] Checkov processor parses JSON results
- [ ] Error handling works for missing files
- [ ] LLM integration functional
- [ ] Logs are properly generated

## Implementation Steps

### Step 1: Create Checkov Execution Script
Create `scripts/tools/run_checkov.sh`:
```bash
#!/bin/bash
# Individual Checkov Scan Script for SimpleSecCheck

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
CHECKOV_CONFIG_PATH="${CHECKOV_CONFIG_PATH:-/SimpleSecCheck/checkov/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_checkov.sh] Initializing Checkov scan..." | tee -a "$LOG_FILE"

if command -v checkov &>/dev/null; then
  echo "[run_checkov.sh][Checkov] Running infrastructure security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CHECKOV_JSON="$RESULTS_DIR/checkov.json"
  CHECKOV_TEXT="$RESULTS_DIR/checkov.txt"
  
  # Check for infrastructure files
  INFRA_FILES=()
  
  # Look for common infrastructure files
  for pattern in "*.tf" "*.tfvars" "*.yml" "*.yaml" "Dockerfile" "*.json"; do
    while IFS= read -r -d '' file; do
      INFRA_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#INFRA_FILES[@]} -eq 0 ]; then
    echo "[run_checkov.sh][Checkov] No infrastructure files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_checkov.sh][Checkov] Found ${#INFRA_FILES[@]} infrastructure file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  checkov -d "$TARGET_PATH" --output json --output-file "$CHECKOV_JSON" 2>>"$LOG_FILE" || {
    echo "[run_checkov.sh][Checkov] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  checkov -d "$TARGET_PATH" --output cli --output-file "$CHECKOV_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_checkov.sh][Checkov] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$CHECKOV_JSON" ] || [ -f "$CHECKOV_TEXT" ]; then
    echo "[run_checkov.sh][Checkov] Scan completed successfully." | tee -a "$LOG_FILE"
    echo "[Checkov] Infrastructure security scan complete." >> "$SUMMARY_TXT"
  else
    echo "[run_checkov.sh][Checkov] No results generated." >> "$LOG_FILE"
  fi
else
  echo "[run_checkov.sh][Checkov] Checkov CLI not found, skipping scan." | tee -a "$LOG_FILE"
fi
```

### Step 2: Create Checkov Processor
Create `scripts/checkov_processor.py`:
```python
#!/usr/bin/env python3
import sys
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[checkov_processor] {msg}", file=sys.stderr)

def checkov_summary(checkov_json):
    findings = []
    if checkov_json and isinstance(checkov_json, dict):
        results = checkov_json.get('results', {})
        failed_checks = results.get('failed_checks', [])
        
        for check in failed_checks:
            finding = {
                'check_id': check.get('check_id', ''),
                'check_name': check.get('check_name', ''),
                'resource': check.get('resource', ''),
                'file_path': check.get('file_path', ''),
                'line_number': check.get('file_line_range', [0])[0] if check.get('file_line_range') else 0,
                'severity': 'HIGH' if 'HIGH' in check.get('check_name', '') or 'CRITICAL' in check.get('check_name', '') else 'MEDIUM',
                'description': check.get('guideline', ''),
                'code_block': check.get('code_block', []),
                'fix': check.get('code_block', [])
            }
            
            prompt = f"Explain this infrastructure security issue: Check {finding['check_id']} ({finding['check_name']}) failed in resource {finding['resource']}. File: {finding['file_path']}. Guideline: {finding['description']}. Suggest how to fix this."
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for Checkov finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            
            findings.append(finding)
    else:
        debug("No Checkov results found in JSON.")
    return findings

def generate_checkov_html_section(checkov_findings):
    html_parts = []
    html_parts.append('<h2>Checkov Infrastructure Security Scan</h2>')
    if checkov_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>Check Name</th><th>Resource</th><th>File</th><th>Severity</th><th>Description</th><th>AI Explanation</th></tr>')
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            icon = '🚨' if sev in ('CRITICAL', 'HIGH') else '⚠️' if sev == 'MEDIUM' else 'ℹ️'
            
            html_parts.append(f'<tr class="row-{sev}"><td>{html.escape(str(finding.get("check_id", "")))}</td><td>{html.escape(str(finding.get("check_name", "")))}</td><td>{html.escape(str(finding.get("resource", "")))}</td><td>{html.escape(str(finding.get("file_path", "")))}</td><td class="severity-{sev}">{icon} {sev}</td><td>{html.escape(str(finding.get("description", "")))}</td><td>{html.escape(str(finding.get("ai_explanation", "")))}</td></tr>')
        html_parts.append('</table>')
        
        severity_counts = {}
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        html_parts.append('<div class="summary-stats">')
        html_parts.append('<h3>Security Issue Summary</h3>')
        html_parts.append('<ul>')
        for sev, count in severity_counts.items():
            html_parts.append(f'<li>{sev}: {count} issues</li>')
        html_parts.append(f'<li><strong>Total: {len(checkov_findings)} security issues</strong></li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No infrastructure security issues found by Checkov.</div>')
    return "".join(html_parts)
```

### Step 3: Make Scripts Executable
```bash
chmod +x scripts/tools/run_checkov.sh
```

## Notes
- Check if this duplicates terraform_security_processor functionality
- Consider consolidating if both handle Checkov scanning

