# Brakeman Integration – Phase 2: Core Implementation

## Overview
This phase implements the core Brakeman functionality by creating the execution script and processor.

## Status: Planning

## Objectives
- [ ] Create Brakeman execution script in scripts/tools/
- [ ] Create Brakeman processor in scripts/
- [ ] Implement JSON report parsing
- [ ] Implement text report generation
- [ ] Add LLM integration for explanations

## Deliverables
- File: `scripts/tools/run_brakeman.sh` - Brakeman execution script
- File: `scripts/brakeman_processor.py` - Brakeman result processor
- Feature: JSON and text report generation
- Feature: LLM integration for AI explanations

## Dependencies
- Requires: Phase 1 (Foundation Setup)
- Blocks: Phase 3 (Integration & Testing)

## Estimated Time
2 hours

## Success Criteria
- [ ] Brakeman execution script is created and functional
- [ ] Brakeman processor parses JSON correctly
- [ ] Reports are generated in JSON and text format
- [ ] LLM integration provides explanations for findings
- [ ] All Brakeman-specific findings are properly formatted

## Implementation Details

### Step 1: Create Brakeman Execution Script
Create `scripts/tools/run_brakeman.sh`:

```bash
#!/bin/bash
# Individual Brakeman Scan Script for SimpleSecCheck

# Expected Environment Variables:
# TARGET_PATH: Path to target directory (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# BRAKEMAN_CONFIG_PATH: Path to Brakeman configuration file

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
BRAKEMAN_CONFIG_PATH="${BRAKEMAN_CONFIG_PATH:-/SimpleSecCheck/brakeman/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_brakeman.sh] Initializing Brakeman scan..." | tee -a "$LOG_FILE"

if command -v brakeman &>/dev/null; then
  echo "[run_brakeman.sh][Brakeman] Running Ruby on Rails security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  BRAKEMAN_JSON="$RESULTS_DIR/brakeman.json"
  BRAKEMAN_TEXT="$RESULTS_DIR/brakeman.txt"
  
  # Check for Ruby/Rails files
  RUBY_FILES=()
  
  # Look for common Ruby/Rails files
  for pattern in "*.rb" "Gemfile" "config/application.rb"; do
    while IFS= read -r -d '' file; do
      RUBY_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#RUBY_FILES[@]} -eq 0 ]; then
    echo "[run_brakeman.sh][Brakeman] No Ruby/Rails files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_brakeman.sh][Brakeman] Found ${#RUBY_FILES[@]} Ruby/Rails file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  if brakeman -q -f json -o "$BRAKEMAN_JSON" "$TARGET_PATH" 2>>"$LOG_FILE"; then
    echo "[run_brakeman.sh][Brakeman] JSON report generation completed." | tee -a "$LOG_FILE"
  else
    echo "[run_brakeman.sh][Brakeman] JSON report generation failed." >> "$LOG_FILE"
  fi
  
  # Generate text report
  if brakeman -q -f plaintext -o "$BRAKEMAN_TEXT" "$TARGET_PATH" 2>>"$LOG_FILE"; then
    echo "[run_brakeman.sh][Brakeman] Text report generation completed." | tee -a "$LOG_FILE"
  else
    echo "[run_brakeman.sh][Brakeman] Text report generation failed." >> "$LOG_FILE"
  fi
  
  if [ -f "$BRAKEMAN_JSON" ] || [ -f "$BRAKEMAN_TEXT" ]; then
    echo "[run_brakeman.sh][Brakeman] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$BRAKEMAN_JSON" ] && echo "  - $BRAKEMAN_JSON" | tee -a "$LOG_FILE"
    [ -f "$BRAKEMAN_TEXT" ] && echo "  - $BRAKEMAN_TEXT" | tee -a "$LOG_FILE"
    echo "[Brakeman] Ruby on Rails security scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_brakeman.sh][Brakeman][ERROR] No Brakeman report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_brakeman.sh][ERROR] Brakeman not found, skipping Ruby security scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### Step 2: Create Brakeman Processor
Create `scripts/brakeman_processor.py` following the existing processor pattern:

```python
#!/usr/bin/env python3
import sys
import html
import json
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[brakeman_processor] {msg}", file=sys.stderr)

def brakeman_summary(brakeman_json):
    findings = []
    if brakeman_json and isinstance(brakeman_json, dict):
        # Parse Brakeman JSON output
        warnings = brakeman_json.get('warnings', [])
        for warning in warnings:
            finding = {
                'warning_type': warning.get('warning_type', ''),
                'warning_code': warning.get('warning_code', ''),
                'message': warning.get('message', ''),
                'file': warning.get('file', ''),
                'line': warning.get('line', ''),
                'link': warning.get('link', ''),
                'confidence': warning.get('confidence', ''),
                'description': warning.get('description', '')
            }
            prompt = f"Explain and suggest a fix for this Brakeman finding: {finding['message']} - Type: {finding['warning_type']} - Confidence: {finding['confidence']}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for Brakeman finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    else:
        debug("No Brakeman results found in JSON.")
    return findings

def generate_brakeman_html_section(brakeman_findings):
    html_parts = []
    html_parts.append('<h2>Brakeman Ruby on Rails Security Scan</h2>')
    if brakeman_findings:
        html_parts.append('<table><tr><th>Type</th><th>Confidence</th><th>File</th><th>Line</th><th>Message</th><th>AI Explanation</th></tr>')
        for finding in brakeman_findings:
            type_escaped = html.escape(str(finding.get('warning_type', '')))
            confidence_escaped = html.escape(str(finding.get('confidence', '')))
            file_escaped = html.escape(str(finding.get('file', '')))
            line_escaped = html.escape(str(finding.get('line', '')))
            message_escaped = html.escape(str(finding.get('message', '')))
            ai_exp_escaped = html.escape(str(finding.get('ai_explanation', '')))
            
            # Add confidence icons
            icon = ''
            conf_class = confidence_escaped.upper()
            if conf_class in ('HIGH', 'CERTAIN'): 
                icon = '🔴'
            elif conf_class == 'MEDIUM': 
                icon = '🟡'
            elif conf_class == 'WEAK': 
                icon = '🟢'
            
            html_parts.append(f'<tr class="row-{conf_class}"><td>{type_escaped}</td><td class="severity-{conf_class}">{icon} {confidence_escaped}</td><td>{file_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Ruby security vulnerabilities found.</div>')
    return "".join(html_parts)
```

## Notes
- Brakeman output format is JSON structured with warnings array
- Each warning has: warning_type, warning_code, message, file, line, link, confidence
- Confidence levels: 0=weak, 1=medium, 2=strong, 3=certain
- Processor needs to handle all Brakeman warning types

