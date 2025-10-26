# ESLint Security Integration – Phase 2: Core Implementation

## Overview
Implement the core ESLint functionality by creating the execution script and results processor for JavaScript/TypeScript security scanning.

## Objectives
- [ ] Create ESLint execution script
- [ ] Create ESLint results processor
- [ ] Implement JSON and text report generation
- [ ] Integrate with LLM explanations
- [ ] Add error handling and logging

## Deliverables
- File: `scripts/tools/run_eslint.sh` - ESLint execution script
- File: `scripts/eslint_processor.py` - ESLint results processor
- Reports: JSON and text output formats

## Dependencies
- Requires: Phase 1 - ESLint Foundation Setup
- Blocks: Phase 3 - System Integration

## Estimated Time
2 hours

## Success Criteria
- [ ] ESLint script executes successfully
- [ ] ESLint generates JSON and text reports
- [ ] ESLint processor parses results correctly
- [ ] HTML section generation works
- [ ] LLM integration functional
- [ ] Error handling works for failed scans

## Implementation Steps

### Step 1: Create ESLint Execution Script
Create `scripts/tools/run_eslint.sh`:
```bash
#!/bin/bash
# Individual ESLint Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
ESLINT_CONFIG_PATH="${ESLINT_CONFIG_PATH:-/SimpleSecCheck/eslint/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_eslint.sh] Initializing ESLint scan..." | tee -a "$LOG_FILE"

if command -v eslint &>/dev/null; then
  echo "[run_eslint.sh][ESLint] Running JavaScript/TypeScript security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  ESLINT_JSON="$RESULTS_DIR/eslint.json"
  ESLINT_TEXT="$RESULTS_DIR/eslint.txt"
  
  # Check for JavaScript/TypeScript files
  JS_FILES=()
  while IFS= read -r -d '' file; do
    JS_FILES+=("$file")
  done < <(find "$TARGET_PATH" -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \) -print0 2>/dev/null)
  
  if [ ${#JS_FILES[@]} -eq 0 ]; then
    echo "[run_eslint.sh][ESLint] No JavaScript/TypeScript files found, skipping scan." | tee -a "$LOG_FILE"
    echo '[]' > "$ESLINT_JSON"
    echo "ESLint: No JavaScript/TypeScript files found" > "$ESLINT_TEXT"
    exit 0
  fi
  
  echo "[run_eslint.sh][ESLint] Found ${#JS_FILES[@]} JavaScript/TypeScript file(s)." | tee -a "$LOG_FILE"
  
  # Run ESLint scan with JSON output
  eslint --format=json --output-file="$ESLINT_JSON" "$TARGET_PATH" || {
    echo "[run_eslint.sh][ESLint] JSON report generation failed." >> "$LOG_FILE"
    echo '[]' > "$ESLINT_JSON"
  }
  
  # Run ESLint scan with text output
  eslint --format=compact --output-file="$ESLINT_TEXT" "$TARGET_PATH" || {
    echo "[run_eslint.sh][ESLint] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$ESLINT_JSON" ]; then
    echo "[run_eslint.sh][ESLint] ESLint scan completed successfully." | tee -a "$LOG_FILE"
    echo "ESLint: JavaScript/TypeScript security scan completed" >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_eslint.sh][ESLint][ERROR] No ESLint report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_eslint.sh][ERROR] eslint not found, skipping ESLint security scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### Step 2: Create ESLint Processor
Create `scripts/eslint_processor.py`:
```python
#!/usr/bin/env python3
import sys
import html
import json
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[eslint_processor] {msg}", file=sys.stderr)

def eslint_summary(eslint_json):
    findings = []
    if eslint_json and isinstance(eslint_json, list):
        for file_result in eslint_json:
            file_path = file_result.get('filePath', '')
            messages = file_result.get('messages', [])
            
            for message in messages:
                finding = {
                    'file_path': file_path,
                    'rule_id': message.get('ruleId', ''),
                    'severity': message.get('severity', 2),
                    'message': message.get('message', ''),
                    'line': message.get('line', 0),
                    'column': message.get('column', 0),
                    'end_line': message.get('endLine', 0),
                    'end_column': message.get('endColumn', 0)
                }
                
                # Skip if severity is 0 (info)
                if finding['severity'] == 0:
                    continue
                
                # Create AI explanation prompt
                prompt = f"Explain this ESLint security issue in {finding['file_path']} at line {finding['line']}: Rule {finding['rule_id']} - {finding['message']}"
                try:
                    if llm_client:
                        finding['ai_explanation'] = llm_client.query(prompt)
                    else:
                        finding['ai_explanation'] = "LLM client not available."
                except Exception as e:
                    debug(f"LLM query failed for ESLint finding: {e}")
                    finding['ai_explanation'] = "Error fetching AI explanation."
                
                findings.append(finding)
    else:
        debug("No ESLint results found in JSON.")
    return findings

def generate_eslint_html_section(eslint_findings):
    html_parts = []
    html_parts.append('<h2>ESLint Security Scan</h2>')
    if eslint_findings:
        html_parts.append('<table><tr><th>File</th><th>Rule</th><th>Severity</th><th>Message</th><th>Line</th><th>AI Explanation</th></tr>')
        for finding in eslint_findings:
            sev = finding['severity']
            sev_text = ''
            icon = ''
            if sev == 1: 
                sev_text = 'WARNING'
                icon = '⚠️'
            elif sev == 2: 
                sev_text = 'ERROR'
                icon = '🚨'
            else: 
                sev_text = 'INFO'
                icon = 'ℹ️'
            
            ai_exp = finding.get('ai_explanation', '')
            
            file_path_escaped = html.escape(str(finding.get("file_path", "")))
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            message_escaped = html.escape(str(finding.get("message", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            ai_exp_escaped = html.escape(str(ai_exp))
            
            html_parts.append(f'<tr class="row-{sev_text}"><td>{file_path_escaped}</td><td>{rule_id_escaped}</td><td class="severity-{sev_text}">{icon} {sev_text}</td><td>{message_escaped}</td><td>{line_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No ESLint security issues found.</div>')
    return "".join(html_parts)
```

### Step 3: Make Script Executable
```bash
chmod +x scripts/tools/run_eslint.sh
```

## Testing
- [ ] Run ESLint script on sample JavaScript file
- [ ] Verify JSON report generation
- [ ] Verify text report generation
- [ ] Test ESLint processor with sample results
- [ ] Test HTML section generation
- [ ] Test LLM integration
- [ ] Test error handling for missing files

## Notes
- ESLint scans will only run on JavaScript/TypeScript files
- Results are filtered to show only warnings and errors (not info)
- LLM explanations help users understand security issues

