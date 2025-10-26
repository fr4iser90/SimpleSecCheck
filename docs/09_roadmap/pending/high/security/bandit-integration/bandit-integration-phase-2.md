# Bandit Integration – Phase 2: Core Implementation

## Overview
This phase implements the core Bandit scanning functionality by creating the execution script and result processor.

## Objectives
- [ ] Create run_bandit.sh script in scripts/tools/
- [ ] Create bandit_processor.py in scripts/
- [ ] Implement JSON and text report generation
- [ ] Add support for Python file scanning

## Deliverables
- File: `scripts/tools/run_bandit.sh` - Bandit execution script
- File: `scripts/bandit_processor.py` - Bandit result processor
- Reports: JSON and text outputs in results directory

## Dependencies
- Requires: Phase 1 completion (Bandit installed and configured)
- Blocks: Phase 3 start

## Estimated Time
2 hours

## Success Criteria
- [ ] Bandit script successfully executes and generates reports
- [ ] Bandit processor correctly parses JSON results
- [ ] HTML sections are generated properly
- [ ] Error handling works for missing files
- [ ] Support for projects without Python files

## Technical Details

### Script Implementation
Create `scripts/tools/run_bandit.sh` with the following structure:

```bash
#!/bin/bash
# Individual Bandit Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
BANDIT_CONFIG_PATH="${BANDIT_CONFIG_PATH:-/SimpleSecCheck/bandit/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_bandit.sh] Initializing Bandit scan..." | tee -a "$LOG_FILE"

if command -v bandit &>/dev/null; then
  echo "[run_bandit.sh][Bandit] Running Python security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  BANDIT_JSON="$RESULTS_DIR/bandit.json"
  BANDIT_TEXT="$RESULTS_DIR/bandit.txt"
  
  # Find Python files to scan
  PYTHON_FILES=$(find "$TARGET_PATH" -name "*.py" -type f 2>/dev/null | wc -l)
  
  if [ "$PYTHON_FILES" -eq 0 ]; then
    echo "[run_bandit.sh][Bandit] No Python files found in $TARGET_PATH" | tee -a "$LOG_FILE"
    echo "[run_bandit.sh][Bandit] Creating empty reports..." | tee -a "$LOG_FILE"
    
    # Create empty JSON report
    echo '{"generated_at": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "metrics": {"_totals": {"loc": 0, "nosec": 0, "skipped_tests": 0, "tests": 0}}, "results": []}' > "$BANDIT_JSON"
    
    # Create empty text report
    echo "Bandit Scan Results" > "$BANDIT_TEXT"
    echo "===================" >> "$BANDIT_TEXT"
    echo "No Python files found." >> "$BANDIT_TEXT"
    echo "Scan completed at: $(date)" >> "$BANDIT_TEXT"
    
    echo "[Bandit] No Python files found." >> "$SUMMARY_TXT"
    exit 0
  fi
  
  echo "[run_bandit.sh][Bandit] Found $PYTHON_FILES Python file(s) to scan..." | tee -a "$LOG_FILE"
  
  # Run Bandit scan with JSON output
  bandit -r "$TARGET_PATH" -f json -o "$BANDIT_JSON" 2>>"$LOG_FILE" || {
    echo "[run_bandit.sh][Bandit] JSON report generation encountered issues." >> "$LOG_FILE"
  }
  
  # Run Bandit scan with text output
  bandit -r "$TARGET_PATH" > "$BANDIT_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_bandit.sh][Bandit] Text report generation encountered issues." >> "$LOG_FILE"
  }
  
  if [ -f "$BANDIT_JSON" ] || [ -f "$BANDIT_TEXT" ]; then
    echo "[run_bandit.sh][Bandit] Bandit scan completed successfully." | tee -a "$LOG_FILE"
    echo "Bandit scan completed - see $BANDIT_JSON and $BANDIT_TEXT" >> "$SUMMARY_TXT"
  else
    echo "[run_bandit.sh][Bandit] No Bandit results generated." | tee -a "$LOG_FILE"
    echo "Bandit scan failed - no results generated" >> "$SUMMARY_TXT"
  fi
else
  echo "[run_bandit.sh][Bandit] Bandit CLI not found. Skipping Bandit scan." | tee -a "$LOG_FILE"
  echo "Bandit scan skipped - CLI not available" >> "$SUMMARY_TXT"
fi

echo "[run_bandit.sh] Bandit scan orchestration completed." | tee -a "$LOG_FILE"
```

### Processor Implementation
Create `scripts/bandit_processor.py` with the following structure:

```python
#!/usr/bin/env python3
import sys
import json
import html
import os

def debug(msg):
    print(f"[bandit_processor] {msg}", file=sys.stderr)

def load_bandit_results(json_file):
    """Load Bandit JSON results file"""
    if not os.path.exists(json_file):
        debug(f"Bandit results file not found: {json_file}")
        return None
    
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        debug(f"Error loading Bandit results: {e}")
        return None

def bandit_summary(bandit_data):
    """Extract summary from Bandit results"""
    findings = []
    if bandit_data and 'results' in bandit_data:
        for result in bandit_data['results']:
            findings.append({
                'test_id': result.get('test_id', ''),
                'test_name': result.get('test_name', ''),
                'severity': result.get('issue_severity', ''),
                'confidence': result.get('issue_confidence', ''),
                'filename': result.get('filename', ''),
                'line_number': result.get('line_number', ''),
                'code': result.get('code', ''),
                'message': result.get('issue_text', '')
            })
    else:
        debug("No Bandit results found in JSON.")
    return findings

def generate_bandit_html_section(bandit_findings):
    """Generate HTML section for Bandit findings"""
    html_parts = []
    html_parts.append('<h2>Bandit Python Security Scan</h2>')
    
    if bandit_findings:
        html_parts.append('<table><tr><th>Test ID</th><th>Severity</th><th>Confidence</th><th>File</th><th>Line</th><th>Issue</th><th>Code</th></tr>')
        for finding in bandit_findings:
            sev = finding['severity'].upper() if finding['severity'] else 'UNKNOWN'
            icon = ''
            if sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            else: icon = 'ℹ️'
            
            filename_escaped = html.escape(str(finding['filename']))
            line_escaped = html.escape(str(finding['line_number']))
            test_id_escaped = html.escape(str(finding['test_id']))
            message_escaped = html.escape(str(finding['message']))
            code_escaped = html.escape(str(finding['code']))
            
            html_parts.append(f'<tr><td>{test_id_escaped}</td><td>{icon} {sev}</td><td>{finding["confidence"]}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td><td>{code_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<p>No Python security vulnerabilities found.</p>')
    
    return '\n'.join(html_parts)

# Main processing logic
if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "/SimpleSecCheck/results"
    bandit_json_file = os.path.join(results_dir, 'bandit.json')
    
    bandit_data = load_bandit_results(bandit_json_file)
    if bandit_data:
        findings = bandit_summary(bandit_data)
        html_section = generate_bandit_html_section(findings)
        print(html_section)
```

### Key Features
- Detection of Python files in target directory
- Generation of JSON and text reports
- Empty report creation if no Python files found
- Proper error handling and logging
- HTML section generation for reports

## Testing Steps
1. Test with sample Python project
2. Test with project having no Python files
3. Verify JSON report structure
4. Verify text report content
5. Check error handling for invalid targets

## Notes
- Bandit scans Python files for security issues
- Results include test ID, severity, confidence, and location
- Processor extracts key information for HTML display
- Script handles projects without Python files gracefully

## Validation Marker
✅ Phase 2 files validated and created: 2025-10-26T08:05:28.000Z

