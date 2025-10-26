# npm audit Integration – Phase 2: Core Implementation

## Overview
Create npm audit script and processor for Node.js dependency vulnerability scanning and report generation.

## Objectives
- [ ] Create npm audit execution script
- [ ] Create npm audit processor for result parsing
- [ ] Implement JSON and text report generation
- [ ] Add support for multiple package.json files
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_npm_audit.sh` - npm audit execution script
- File: `scripts/npm_audit_processor.py` - npm audit result processor
- Feature: JSON and text report generation
- Feature: Multiple package.json support
- Feature: LLM integration for explanations

## Dependencies
- Requires: Phase 1 - Foundation Setup completion
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] npm audit script generates JSON and text reports
- [ ] npm audit processor parses results correctly
- [ ] npm audit processor generates HTML sections
- [ ] npm audit processor integrates with LLM explanations
- [ ] npm audit script handles multiple package.json files
- [ ] Error handling works for failed scans or missing npm

## Technical Details

### npm audit Script Implementation
```bash
#!/bin/bash
# Individual npm audit Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
NPM_AUDIT_CONFIG_PATH="${NPM_AUDIT_CONFIG_PATH:-/SimpleSecCheck/npm-audit/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_npm_audit.sh] Initializing npm audit scan..." | tee -a "$LOG_FILE"

if command -v npm &>/dev/null; then
  echo "[run_npm_audit.sh][npm audit] Running npm dependency security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  NPM_AUDIT_JSON="$RESULTS_DIR/npm-audit.json"
  NPM_AUDIT_TEXT="$RESULTS_DIR/npm-audit.txt"
  
  # Check for Node.js/JavaScript dependency files
  DEPENDENCY_FILES=()
  
  # Look for package.json files
  while IFS= read -r -d '' file; do
    DEPENDENCY_FILES+=("$file")
  done < <(find "$TARGET_PATH" -name "package.json" -type f -print0 2>/dev/null)
  
  if [ ${#DEPENDENCY_FILES[@]} -eq 0 ]; then
    echo "[run_npm_audit.sh][npm audit] No package.json files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_npm_audit.sh][npm audit] Found ${#DEPENDENCY_FILES[@]} package.json file(s)." | tee -a "$LOG_FILE"
  
  # Scan each package.json directory
  VULNS_FOUND=0
  for package_json in "${DEPENDENCY_FILES[@]}"; do
    dir=$(dirname "$package_json")
    echo "[run_npm_audit.sh][npm audit] Scanning directory: $dir" | tee -a "$LOG_FILE"
    
    # Generate JSON report
    cd "$dir" && npm audit --json > "$NPM_AUDIT_JSON-$VULNS_FOUND" 2>>"$LOG_FILE" || {
      echo "[run_npm_audit.sh][npm audit] JSON report generation failed for $dir" >> "$LOG_FILE"
    }
    
    # Generate text report
    cd "$dir" && npm audit > "$NPM_AUDIT_TEXT-$VULNS_FOUND" 2>>"$LOG_FILE" || {
      echo "[run_npm_audit.sh][npm audit] Text report generation failed for $dir" >> "$LOG_FILE"
    }
    
    VULNS_FOUND=$((VULNS_FOUND + 1))
  done
  
  # Combine all results into single files (if multiple found)
  if [ $VULNS_FOUND -gt 0 ]; then
    if [ -f "$NPM_AUDIT_JSON-0" ]; then
      cp "$NPM_AUDIT_JSON-0" "$NPM_AUDIT_JSON"
    fi
    if [ -f "$NPM_AUDIT_TEXT-0" ]; then
      cp "$NPM_AUDIT_TEXT-0" "$NPM_AUDIT_TEXT"
    fi
    rm -f "$NPM_AUDIT_JSON"-* "$NPM_AUDIT_TEXT"-*
    
    echo "[run_npm_audit.sh][npm audit] Scan completed. Found $VULNS_FOUND package.json files." | tee -a "$LOG_FILE"
    echo "npm audit: Completed" >> "$SUMMARY_TXT"
  else
    echo "[run_npm_audit.sh][npm audit] No vulnerabilities found." | tee -a "$LOG_FILE"
    echo "npm audit: No vulnerabilities" >> "$SUMMARY_TXT"
  fi
else
  echo "[run_npm_audit.sh][npm audit] npm command not found, skipping npm audit scan." | tee -a "$LOG_FILE"
fi
```

### npm audit Processor Implementation
```python
#!/usr/bin/env python3
import sys
import html
import json
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[npm_audit_processor] {msg}", file=sys.stderr)

def npm_audit_summary(npm_audit_json):
    findings = []
    if npm_audit_json and isinstance(npm_audit_json, dict):
        # Handle npm audit JSON format
        vulnerabilities = npm_audit_json.get('vulnerabilities', {})
        metadata = npm_audit_json.get('metadata', {})
        
        for package_name, vuln_data in vulnerabilities.items():
            finding = {
                'package': vuln_data.get('name', package_name),
                'severity': vuln_data.get('severity', 'MODERATE'),
                'is_direct': vuln_data.get('isDirect', False),
                'via': vuln_data.get('via', []),
                'effects': vuln_data.get('effects', []),
                'range': vuln_data.get('range', ''),
                'fix_available': vuln_data.get('fixAvailable', False),
                'dependency_path': ' > '.join(vuln_data.get('nodes', []))
            }
            
            # Create AI explanation prompt
            prompt = f"Explain this npm security vulnerability: Package {finding['package']} has severity {finding['severity']}. {finding.get('via', 'No additional details')}. Suggest how to fix this."
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for npm audit finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            
            findings.append(finding)
    else:
        debug("No npm audit results found in JSON.")
    return findings

def generate_npm_audit_html_section(npm_audit_findings):
    html_parts = []
    html_parts.append('<h2>npm audit Dependency Security Scan</h2>')
    if npm_audit_findings:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>Is Direct</th><th>Dependency Path</th><th>Fix Available</th><th>AI Explanation</th></tr>')
        for finding in npm_audit_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MODERATE': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            ai_exp = finding.get('ai_explanation', '')
            is_direct = 'Yes' if finding.get('is_direct') else 'No'
            fix_available = 'Yes' if finding.get('fix_available') else 'No'
            
            package_escaped = html.escape(str(finding.get("package", "")))
            sev_escaped = html.escape(str(sev))
            is_direct_escaped = html.escape(str(is_direct))
            dep_path_escaped = html.escape(str(finding.get("dependency_path", "")))
            fix_available_escaped = html.escape(str(fix_available))
            ai_exp_escaped = html.escape(str(ai_exp))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{package_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{is_direct_escaped}</td><td>{dep_path_escaped}</td><td>{fix_available_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No npm dependency vulnerabilities found.</div>')
    return "".join(html_parts)
```

### Integration Points
- Script: `scripts/tools/run_npm_audit.sh`
- Processor: `scripts/npm_audit_processor.py`
- HTML Generation: Uses existing LLM connector for explanations
- Report Format: JSON and text outputs like other tools

### Testing Checklist
- [ ] Test with single package.json
- [ ] Test with multiple package.json files
- [ ] Test error handling when npm not available
- [ ] Test with no vulnerabilities found
- [ ] Test with various severity levels
- [ ] Test LLM explanation integration
- [ ] Test HTML section generation

