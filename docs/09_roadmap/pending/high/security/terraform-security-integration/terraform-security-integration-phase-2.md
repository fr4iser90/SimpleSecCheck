# Terraform Security Integration – Phase 2: Core Implementation

## Overview
Create Checkov script and processor for Terraform security scanning and report generation.

## Objectives
- [ ] Create Terraform security execution script
- [ ] Create Checkov processor for result parsing
- [ ] Implement JSON and text report generation
- [ ] Add support for Terraform file detection
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_terraform_security.sh` - Checkov execution script
- File: `scripts/terraform_security_processor.py` - Checkov result processor
- Feature: JSON and text report generation
- Feature: Terraform file pattern detection
- Feature: LLM integration for explanations

## Dependencies
- Requires: Phase 1 - Foundation Setup completion
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov script generates JSON and text reports
- [ ] Checkov processor parses results correctly
- [ ] Checkov processor generates HTML sections
- [ ] Checkov processor integrates with LLM explanations
- [ ] Checkov script handles Terraform file detection
- [ ] Error handling works for failed scans

## Technical Details

### Checkov Script Implementation
Location: `scripts/tools/run_terraform_security.sh`

```bash
#!/bin/bash
# Individual Terraform Security Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
TERRAFORM_SECURITY_CONFIG_PATH="${TERRAFORM_SECURITY_CONFIG_PATH:-/SimpleSecCheck/terraform-security/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_terraform_security.sh] Initializing Terraform security scan..." | tee -a "$LOG_FILE"

if command -v checkov &>/dev/null; then
  echo "[run_terraform_security.sh][Checkov] Running Terraform security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CHECKOV_JSON="$RESULTS_DIR/checkov.json"
  CHECKOV_TEXT="$RESULTS_DIR/checkov.txt"
  
  # Check for Terraform files
  TERRAFORM_FILES=()
  
  # Look for common Terraform files
  for pattern in "*.tf" "*.tfvars"; do
    while IFS= read -r -d '' file; do
      TERRAFORM_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#TERRAFORM_FILES[@]} -eq 0 ]; then
    echo "[run_terraform_security.sh][Checkov] No Terraform files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_terraform_security.sh][Checkov] Found ${#TERRAFORM_FILES[@]} Terraform file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  checkov -d "$TARGET_PATH" --framework terraform --output json --output-file "$CHECKOV_JSON" 2>>"$LOG_FILE" || {
    echo "[run_terraform_security.sh][Checkov] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  checkov -d "$TARGET_PATH" --framework terraform --output cli --output-file "$CHECKOV_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_terraform_security.sh][Checkov] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$CHECKOV_JSON" ] || [ -f "$CHECKOV_TEXT" ]; then
    echo "[run_terraform_security.sh][Checkov] Scan completed successfully." | tee -a "$LOG_FILE"
    echo "[Checkov] Terraform security scan complete." >> "$SUMMARY_TXT"
  else
    echo "[run_terraform_security.sh][Checkov] No results generated." >> "$LOG_FILE"
  fi
else
  echo "[run_terraform_security.sh][Checkov] Checkov CLI not found, skipping scan." | tee -a "$LOG_FILE"
fi
```

### Checkov Processor Implementation
Location: `scripts/terraform_security_processor.py`

```python
#!/usr/bin/env python3
import sys
import html
import json
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[terraform_security_processor] {msg}", file=sys.stderr)

def checkov_summary(checkov_json):
    findings = []
    if checkov_json and isinstance(checkov_json, dict):
        # Handle Checkov JSON format
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
            
            # Create AI explanation prompt
            prompt = f"Explain this Terraform security issue: Check {finding['check_id']} ({finding['check_name']}) failed in resource {finding['resource']}. File: {finding['file_path']}. Guideline: {finding['description']}. Suggest how to fix this."
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
    html_parts.append('<h2>Checkov Terraform Security Scan</h2>')
    if checkov_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>Check Name</th><th>Resource</th><th>File</th><th>Severity</th><th>Description</th><th>AI Explanation</th></tr>')
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            ai_exp = finding.get('ai_explanation', '')
            
            check_id_escaped = html.escape(str(finding.get("check_id", "")))
            check_name_escaped = html.escape(str(finding.get("check_name", "")))
            resource_escaped = html.escape(str(finding.get("resource", "")))
            file_path_escaped = html.escape(str(finding.get("file_path", "")))
            sev_escaped = html.escape(str(sev))
            desc_escaped = html.escape(str(finding.get("description", "")))
            ai_exp_escaped = html.escape(str(ai_exp))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{check_id_escaped}</td><td>{check_name_escaped}</td><td>{resource_escaped}</td><td>{file_path_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{desc_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
        
        # Add summary statistics
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
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Terraform security issues found by Checkov.</div>')
    return "".join(html_parts)
```

## Implementation Steps

### Step 1: Create Checkov Script
1. Create file: `scripts/tools/run_terraform_security.sh`
2. Add content from Technical Details section
3. Make executable: `chmod +x scripts/tools/run_terraform_security.sh`

### Step 2: Create Checkov Processor
1. Create file: `scripts/terraform_security_processor.py`
2. Add content from Technical Details section
3. Ensure LLM connector import works

### Step 3: Validate Scripts
1. Test Checkov script with sample Terraform code
2. Verify JSON report generation
3. Verify text report generation
4. Test processor with sample JSON output

## Testing
- Create sample Terraform files (.tf)
- Run Checkov script manually
- Verify reports are generated
- Test processor with sample JSON
- Validate HTML generation

## Notes
- Checkov supports multiple cloud providers (AWS, Azure, GCP)
- JSON format may vary by Checkov version
- Error handling must be comprehensive
- Follow existing script patterns

