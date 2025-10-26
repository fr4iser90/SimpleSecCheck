# Wapiti Integration – Phase 2: Core Implementation

## Overview
Create Wapiti execution script and result processor. This phase implements the core functionality for running Wapiti scans and processing results.

## Objectives
- [x] Create run_wapiti.sh execution script
- [x] Create wapiti_processor.py for result processing
- [x] Implement JSON and text report generation
- [x] Integrate with LLM for explanations

## Deliverables
- [x] File: `scripts/tools/run_wapiti.sh` - Wapiti execution script
- [x] File: `scripts/wapiti_processor.py` - Result processor
- [x] File: `results/wapiti.json` - JSON report output
- [x] File: `results/wapiti.txt` - Text report output

## Dependencies
- Requires: Phase 1 completion (Wapiti installation)
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] run_wapiti.sh executes Wapiti scans
- [ ] wapiti_processor.py processes Wapiti JSON output
- [ ] HTML sections generated correctly
- [ ] LLM explanations integrated

## Technical Details

### 2.1 Execution Script
Create `scripts/tools/run_wapiti.sh`:
```bash
#!/bin/bash
# Individual Wapiti Scan Script for SimpleSecCheck

set -e

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
WAPITI_CONFIG_PATH="${WAPITI_CONFIG_PATH:-/SimpleSecCheck/wapiti/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

log_wapiti_action() {
    echo "[run_wapiti.sh] ($(date '+%Y-%m-%d %H:%M:%S')) ($BASHPID) $1" | tee -a "$LOG_FILE"
}

log_wapiti_action "Initializing Wapiti scan..."
log_wapiti_action "Target: $ZAP_TARGET"

if command -v wapiti &>/dev/null; then
    WAPITI_JSON="$RESULTS_DIR/wapiti.json"
    WAPITI_TEXT="$RESULTS_DIR/wapiti.txt"
    
    log_wapiti_action "Running Wapiti scan on $ZAP_TARGET..."
    
    # Run Wapiti scan with JSON output
    wapiti -u "$ZAP_TARGET" -f json -o "$WAPITI_JSON" >>"$LOG_FILE" 2>&1 || {
        log_wapiti_action "Wapiti JSON report generation failed."
    }
    
    # Run Wapiti scan with text output
    wapiti -u "$ZAP_TARGET" -o "$WAPITI_TEXT" >>"$LOG_FILE" 2>&1 || {
        log_wapiti_action "Wapiti text report generation failed."
    }
    
    if [ -f "$WAPITI_JSON" ] || [ -f "$WAPITI_TEXT" ]; then
        log_wapiti_action "Wapiti scan complete."
        echo "[Wapiti] Web vulnerability scan complete." >> "$SUMMARY_TXT"
        exit 0
    else
        log_wapiti_action "[ERROR] No Wapiti report generated!"
        exit 1
    fi
else
    log_wapiti_action "[ERROR] wapiti command not found."
    exit 1
fi
```

### 2.2 Result Processor
Create `scripts/wapiti_processor.py`:
```python
#!/usr/bin/env python3
import sys
import json
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[wapiti_processor] {msg}", file=sys.stderr)

def wapiti_summary(wapiti_json):
    findings = []
    if wapiti_json and isinstance(wapiti_json, dict):
        vulnerabilities = wapiti_json.get('vulnerabilities', [])
        for vuln in vulnerabilities:
            finding = {
                'category': vuln.get('category', ''),
                'description': vuln.get('description', ''),
                'reference': vuln.get('reference', ''),
                'status': vuln.get('status', ''),
                'target': vuln.get('target', '')
            }
            prompt = f"Explain and suggest a fix for this Wapiti finding: {finding['description']} - Category: {finding['category']}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    return findings

def generate_wapiti_html_section(wapiti_findings):
    html_parts = []
    html_parts.append('<h2>Wapiti Web Vulnerability Scan</h2>')
    if wapiti_findings:
        html_parts.append('<table><tr><th>Category</th><th>Description</th><th>Target</th><th>AI Explanation</th></tr>')
        for finding in wapiti_findings:
            category = finding.get('category', '')
            description = finding.get('description', '')
            target = finding.get('target', '')
            ai_exp = finding.get('ai_explanation', '')
            html_parts.append(f'<tr><td>{category}</td><td>{description}</td><td>{target}</td><td>{ai_exp}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear">✅ All clear! No vulnerabilities found.</div>')
    return "".join(html_parts)
```

### 2.3 HTML Report Integration
Update `scripts/generate-html-report.py` to include Wapiti:
```python
from scripts import wapiti_processor

# In the report generation section:
wapiti_json_path = Path(results_dir) / "wapiti.json"
if wapiti_json_path.exists():
    with open(wapiti_json_path, 'r') as f:
        wapiti_data = json.load(f)
    wapiti_findings = wapiti_processor.wapiti_summary(wapiti_data)
    wapiti_section = wapiti_processor.generate_wapiti_html_section(wapiti_findings)
    html_parts.append(wapiti_section)
```

## Notes
- Follow existing patterns from ZAP and Nuclei processors
- Use standard logging format with tee -a
- Handle errors gracefully with proper exit codes
- Integrate LLM for vulnerability explanations

