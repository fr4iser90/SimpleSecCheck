# Nikto Integration – Phase 2: Core Implementation

## Overview
Implement Nikto execution script and processor to scan web applications and process results for reporting.

## Objectives
- [ ] Create Nikto execution script (run_nikto.sh)
- [ ] Create Nikto processor (nikto_processor.py)
- [ ] Generate JSON and text reports
- [ ] Integrate with LLM explanations

## Deliverables
- [ ] File: `scripts/tools/run_nikto.sh` - Nikto execution script
- [ ] File: `scripts/nikto_processor.py` - Nikto result processor
- [ ] Report generation with multiple formats
- [ ] LLM integration for findings

## Dependencies
- Requires: Phase 1 completion (Nikto installed)
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] run_nikto.sh executes Nikto scans successfully
- [ ] nikto_processor.py processes results correctly
- [ ] JSON and text reports generated
- [ ] LLM explanations integrated
- [ ] Error handling implemented

## Technical Details

### 2.1 Nikto Script Creation
Create `scripts/tools/run_nikto.sh`:
```bash
#!/bin/bash
# Individual Nikto Scan Script for SimpleSecCheck

# Expected Environment Variables:
# ZAP_TARGET: Target URL to scan (e.g., http://host.docker.internal:8000)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
NIKTO_CONFIG_PATH="${NIKTO_CONFIG_PATH:-/SimpleSecCheck/nikto/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_nikto.sh] Initializing Nikto scan..." | tee -a "$LOG_FILE"

if command -v nikto &>/dev/null; then
  echo "[run_nikto.sh][Nikto] Running web server scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  
  NIKTO_JSON="$RESULTS_DIR/nikto.json"
  NIKTO_TEXT="$RESULTS_DIR/nikto.txt"
  
  # Run Nikto scan with JSON output
  echo "[run_nikto.sh][Nikto] Running web server scan..." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  nikto -h "$ZAP_TARGET" -Format json -output "$NIKTO_JSON" 2>>"$LOG_FILE" || {
    echo "[run_nikto.sh][Nikto] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  nikto -h "$ZAP_TARGET" -output "$NIKTO_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_nikto.sh][Nikto] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$NIKTO_JSON" ] || [ -f "$NIKTO_TEXT" ]; then
    echo "[run_nikto.sh][Nikto] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$NIKTO_JSON" ] && echo "  - $NIKTO_JSON" | tee -a "$LOG_FILE"
    [ -f "$NIKTO_TEXT" ] && echo "  - $NIKTO_TEXT" | tee -a "$LOG_FILE"
    echo "[Nikto] Web server scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_nikto.sh][Nikto][ERROR] No Nikto report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_nikto.sh][ERROR] nikto not found, skipping web server scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Nikto is a core tool
fi
```

### 2.2 Nikto Processor Creation
Create `scripts/nikto_processor.py`:
```python
#!/usr/bin/env python3
import sys
import json
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[nikto_processor] {msg}", file=sys.stderr)

def nikto_summary(nikto_json):
    findings = []
    if nikto_json and isinstance(nikto_json, dict):
        # Parse Nikto JSON output
        scan_details = nikto_json.get('scan_details', {})
        for host, details in scan_details.items():
            # Extract findings
            items = details.get('items', [])
            for item in items:
                finding = {
                    'osvdb': item.get('osvdb', ''),
                    'osvdb_link': item.get('osvdb_link', ''),
                    'name': item.get('name', ''),
                    'description': item.get('description', ''),
                    'full_name': item.get('full_name', ''),
                    'target_ip': details.get('target_ip', ''),
                    'host_ip': details.get('host_ip', '')
                }
                prompt = f"Explain and suggest a fix for this Nikto finding: {finding['description']} - Name: {finding['name']}"
                try:
                    if llm_client:
                        finding['ai_explanation'] = llm_client.query(prompt)
                    else:
                        finding['ai_explanation'] = "LLM client not available."
                except Exception as e:
                    debug(f"LLM query failed for Nikto finding: {e}")
                    finding['ai_explanation'] = "Error fetching AI explanation."
                findings.append(finding)
    else:
        debug("No Nikto results found in JSON.")
    return findings

def generate_nikto_html_section(nikto_findings):
    html_parts = []
    html_parts.append('<h2>Nikto Web Server Scan</h2>')
    if nikto_findings:
        html_parts.append('<table><tr><th>Finding</th><th>Description</th><th>AI Explanation</th></tr>')
        for finding in nikto_findings:
            name_escaped = html.escape(str(finding.get('name', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            ai_exp_escaped = html.escape(str(finding.get('ai_explanation', '')))
            html_parts.append(f'<tr><td>{name_escaped}</td><td>{description_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>')
    return "".join(html_parts)
```

## Notes
- Nikto JSON format needs careful parsing due to nested structure
- Handle different Nikto output versions
- Integration with LLM for finding explanations
- Follow processor patterns from Wapiti and ZAP processors

## Implementation Steps
1. Create run_nikto.sh with error handling
2. Create nikto_processor.py following existing processor patterns
3. Implement JSON parsing for Nikto output
4. Add LLM integration for findings
5. Implement HTML section generation
6. Test with sample Nikto output

