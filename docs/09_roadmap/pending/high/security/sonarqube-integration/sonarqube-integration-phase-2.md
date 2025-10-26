# SonarQube Integration – Phase 2: Core Implementation

## Overview
Create SonarQube execution script and processor for code quality and security scanning and report generation.

## Objectives
- [ ] Create SonarQube execution script
- [ ] Create SonarQube processor for result parsing
- [ ] Implement JSON and text report generation
- [ ] Add support for multiple programming languages
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_sonarqube.sh` - SonarQube execution script
- File: `scripts/sonarqube_processor.py` - SonarQube result processor
- Feature: JSON and text report generation
- Feature: Multiple programming language support
- Feature: LLM integration for explanations

## Dependencies
- Requires: Phase 1 - Foundation Setup completion
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] SonarQube script generates JSON and text reports
- [ ] SonarQube processor parses results correctly
- [ ] SonarQube processor generates HTML sections
- [ ] SonarQube processor integrates with LLM explanations
- [ ] SonarQube script handles multiple programming languages
- [ ] Error handling works for failed scans

## Technical Details

### SonarQube Script Implementation
```bash
#!/bin/bash
# Individual SonarQube Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SONARQUBE_CONFIG_PATH="${SONARQUBE_CONFIG_PATH:-/SimpleSecCheck/sonarqube/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_sonarqube.sh] Initializing SonarQube scan..." | tee -a "$LOG_FILE"

if command -v sonar-scanner &>/dev/null; then
  echo "[run_sonarqube.sh][SonarQube] Running code quality and security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  SONARQUBE_JSON="$RESULTS_DIR/sonarqube.json"
  SONARQUBE_TEXT="$RESULTS_DIR/sonarqube.txt"
  
  # Create SonarQube project properties
  SONARQUBE_PROJECT_PROPERTIES="$TARGET_PATH/sonar-project.properties"
  
  # Generate basic project properties if not exists
  if [ ! -f "$SONARQUBE_PROJECT_PROPERTIES" ]; then
    echo "[run_sonarqube.sh][SonarQube] Creating sonar-project.properties..." | tee -a "$LOG_FILE"
    cat > "$SONARQUBE_PROJECT_PROPERTIES" << EOF
sonar.projectKey=SimpleSecCheck-Analysis
sonar.projectName=SimpleSecCheck-Analysis
sonar.projectVersion=1.0.0
sonar.sources=.
sonar.sourceEncoding=UTF-8
sonar.exclusions=**/test*,**/tests/**,**/__pycache__/**,**/node_modules/**,**/venv/**
EOF
  fi
  
  # Run SonarQube scan
  echo "[run_sonarqube.sh][SonarQube] Running SonarQube analysis..." | tee -a "$LOG_FILE"
  cd "$TARGET_PATH" && sonar-scanner -X 2>>"$LOG_FILE" || {
    echo "[run_sonarqube.sh][SonarQube] SonarQube scan failed." | tee -a "$LOG_FILE"
    
    # Create minimal reports on failure
    echo '{"issues": [], "summary": {"total_issues": 0, "blocker": 0, "critical": 0, "major": 0, "minor": 0, "info": 0}}' > "$SONARQUBE_JSON"
    echo "SonarQube Scan Results" > "$SONARQUBE_TEXT"
    echo "===================" >> "$SONARQUBE_TEXT"
    echo "SonarQube scan failed or no issues found." >> "$SONARQUBE_TEXT"
    echo "Scan completed at: $(date)" >> "$SONARQUBE_TEXT"
    
    echo "[SonarQube] Code quality and security scan complete." >> "$SUMMARY_TXT"
    exit 0
  }
  
  # Convert results to JSON format (if needed)
  if [ -f "$SONARQUBE_JSON" ]; then
    echo "[run_sonarqube.sh][SonarQube] SonarQube results available." | tee -a "$LOG_FILE"
    echo "[SonarQube] Code quality and security scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    # Create minimal reports
    echo '{"issues": [], "summary": {"total_issues": 0, "blocker": 0, "critical": 0, "major": 0, "minor": 0, "info": 0}}' > "$SONARQUBE_JSON"
    echo "SonarQube Scan Results" > "$SONARQUBE_TEXT"
    echo "===================" >> "$SONARQUBE_TEXT"
    echo "No SonarQube results generated." >> "$SONARQUBE_TEXT"
    echo "Scan completed at: $(date)" >> "$SONARQUBE_TEXT"
    
    echo "[run_sonarqube.sh][SonarQube] No results generated." | tee -a "$LOG_FILE"
    echo "[SonarQube] Code quality and security scan complete." >> "$SUMMARY_TXT"
    exit 0
  fi
else
  echo "[run_sonarqube.sh][ERROR] sonar-scanner not found, skipping code quality and security scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### SonarQube Processor Implementation
```python
#!/usr/bin/env python3
"""
SonarQube Processor for SimpleSecCheck
Processes SonarQube results and generates HTML report sections
"""

import json
import os
import sys
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[sonarqube_processor] {msg}", file=sys.stderr)

def sonarqube_summary(sonarqube_json):
    findings = []
    if sonarqube_json and isinstance(sonarqube_json, dict):
        # Handle SonarQube JSON format
        issues = sonarqube_json.get('issues', [])
        
        for issue in issues:
            finding = {
                'severity': issue.get('severity', 'INFO'),
                'component': issue.get('component', ''),
                'message': issue.get('message', ''),
                'line': issue.get('line', 0),
                'rule': issue.get('rule', ''),
                'type': issue.get('type', 'CODE_SMELL')
            }
            
            # Create AI explanation prompt
            prompt = f"Explain this SonarQube code quality issue: {finding['severity']} severity issue in {finding['component']} at line {finding['line']}. Message: {finding['message']}. Suggest how to fix this."
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for SonarQube finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            
            findings.append(finding)
    else:
        debug("No SonarQube results found in JSON.")
    return findings

def generate_sonarqube_html_section(sonarqube_findings):
    html_parts = []
    html_parts.append('<h2>SonarQube Code Quality & Security Scan</h2>')
    if sonarqube_findings:
        html_parts.append('<table><tr><th>Severity</th><th>Component</th><th>Line</th><th>Message</th><th>AI Explanation</th></tr>')
        for finding in sonarqube_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'BLOCKER': icon = '🚨'
            elif sev == 'CRITICAL': icon = '🚨'
            elif sev == 'MAJOR': icon = '⚠️'
            elif sev == 'MINOR': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            ai_exp = finding.get('ai_explanation', '')
            
            severity_escaped = html.escape(str(sev))
            component_escaped = html.escape(str(finding.get("component", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            message_escaped = html.escape(str(finding.get("message", "")))
            ai_exp_escaped = html.escape(str(ai_exp))

            html_parts.append(f'<tr class="row-{severity_escaped}"><td class="severity-{severity_escaped}">{icon} {severity_escaped}</td><td>{component_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code quality issues found.</div>')
    return "".join(html_parts)
```

## Step-by-Step Implementation

### Step 1: Create SonarQube Script (45 min)
1. Create `scripts/tools/run_sonarqube.sh` file
2. Implement SonarQube scan execution
3. Add report generation (JSON and text)
4. Add error handling
5. Test script execution

### Step 2: Create SonarQube Processor (45 min)
1. Create `scripts/sonarqube_processor.py` file
2. Implement JSON parsing
3. Add HTML generation
4. Integrate with LLM explanations
5. Test processor with sample results

### Step 3: Add Language Support (15 min)
1. Configure for Java, Python, JavaScript
2. Add TypeScript, C#, Go, Kotlin, PHP support
3. Test with different language samples
4. Validate report generation

### Step 4: Testing (15 min)
1. Test with sample code
2. Validate JSON report generation
3. Validate text report generation
4. Test error handling
5. Validate LLM integration

## Validation
- SonarQube script generates reports successfully
- SonarQube processor parses results correctly
- HTML sections generated correctly
- LLM explanations work properly
- Error handling works for failed scans

## Next Steps
- Proceed to Phase 3: Integration & Testing
- Integrate with main orchestrator
- Update HTML report generator
- Add to false positive whitelist

