# Terraform Security Integration - Implementation Plan

## 1. Project Overview
- **Feature/Component Name**: Terraform Security Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Infrastructure security scanning
- **Created**: 2025-10-25T23:44:26.000Z
- **Last Updated**: 2025-10-26T00:14:22.000Z

## 2. Technical Requirements
- **Tech Stack**: Python, Bash, Checkov (Terraform security scanner)
- **Architecture Pattern**: Modular tool integration
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: HTML report generation
- **Backend Changes**: Checkov processor, script creation

## 3. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py, snyk_processor.py, sonarqube_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

## 4. Implementation Phases

#### Phase 1: Foundation Setup (2 hours)
- [ ] Checkov Installation: Add Checkov to Dockerfile
- [ ] Checkov Configuration: Create terraform-security/ directory with config.yaml
- [ ] Environment Setup: Set up Terraform security scanning parameters

#### Phase 2: Core Implementation (2 hours)
- [ ] Checkov Script Creation: Create scripts/tools/run_terraform_security.sh
- [ ] Checkov Processor Creation: Create scripts/terraform_security_processor.py
- [ ] Report Generation: Generate JSON and text reports
- [ ] LLM Integration: Integrate with LLM explanations

#### Phase 3: Integration & Testing (2 hours)
- [ ] System Integration: Update scripts/security-check.sh
- [ ] Dockerfile Updates: Add Checkov to Dockerfile
- [ ] HTML Report Updates: Update generate-html-report.py
- [ ] False Positive Support: Add Checkov to fp_whitelist.json
- [ ] Testing: Test with sample Terraform projects

## 5. File Impact Analysis

#### Files to Modify:
- [ ] `Dockerfile` - Add Checkov installation
- [ ] `scripts/security-check.sh` - Add Checkov orchestration
- [ ] `scripts/generate-html-report.py` - Add Checkov processing
- [ ] `scripts/html_utils.py` - Add Checkov to summaries
- [ ] `conf/fp_whitelist.json` - Add Checkov support

#### Files to Create:
- [ ] `terraform-security/config.yaml` - Checkov configuration
- [ ] `scripts/tools/run_terraform_security.sh` - Checkov execution script
- [ ] `scripts/terraform_security_processor.py` - Checkov result processor

#### Files to Delete:
- [ ] None

## 6. Code Standards & Patterns
- **Coding Style**: Follow existing Python and Bash patterns
- **Naming Conventions**: Use terraform_security for file names
- **Error Handling**: Comprehensive error handling with logging
- **Logging**: Use tee -a for log file appending
- **Testing**: Test with sample Terraform projects
- **Documentation**: Update README with Checkov integration

## 7. Security Considerations
- [ ] Checkov scans for Terraform security misconfigurations
- [ ] Supports cloud provider configurations (AWS, Azure, GCP)
- [ ] Identifies infrastructure security issues
- [ ] Checks for exposed secrets and credentials
- [ ] Validates resource configurations

## 8. Performance Requirements
- **Response Time**: Scan should complete within 5 minutes for typical projects
- **Throughput**: Support multiple Terraform modules
- **Memory Usage**: Efficient JSON processing
- **Database Queries**: None
- **Caching Strategy**: Not applicable

## 9. Testing Strategy
#### Unit Tests:
- [ ] Test Checkov processor with sample JSON
- [ ] Test HTML generation
- [ ] Test error handling

#### Integration Tests:
- [ ] Test full scan workflow
- [ ] Test report generation
- [ ] Test LLM integration

#### E2E Tests:
- [ ] Test with sample Terraform projects
- [ ] Test with real-world configurations

## 10. Documentation Requirements
- [ ] Update README.md with Checkov integration
- [ ] Document configuration options
- [ ] Add examples of Terraform scans

## 11. Deployment Checklist
- [ ] Checkov installed in Docker container
- [ ] Configuration files created
- [ ] Scripts executable
- [ ] Processors integrated
- [ ] HTML reports updated

## 12. Rollback Plan
- [ ] Keep Terraform security scanning optional
- [ ] Gracefully handle Checkov failures
- [ ] Maintain backward compatibility

## 13. Success Criteria
- [ ] Checkov installed and functional in Docker container
- [ ] Checkov script generates JSON and text reports
- [ ] Checkov processor parses results correctly
- [ ] Checkov processor generates HTML sections
- [ ] Checkov processor integrates with LLM explanations
- [ ] Error handling works for failed scans
- [ ] Integration with main orchestrator works
- [ ] HTML report includes Checkov results
- [ ] Visual summary includes Checkov status
- [ ] Overall summary includes Checkov findings
- [ ] Links section includes Checkov reports

## 14. AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/terraform-security-integration/terraform-security-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

## 15. Risk Assessment
- **Low Risk**: Adding one security scanner integration
- **Mitigation**: Follow existing tool integration patterns
- **Testing**: Comprehensive testing with sample projects
- **Rollback**: Optional tool, fails gracefully

## 16. Implementation Details

### Checkov Installation (Dockerfile)
```dockerfile
# Install Checkov (Terraform security scanner)
RUN pip3 install checkov
```

### Checkov Configuration (terraform-security/config.yaml)
```yaml
# Checkov Configuration for SimpleSecCheck
version: "1.0"

# Scan settings
scan:
  # Terraform file patterns to scan
  file_patterns:
    - "*.tf"
    - "*.tfvars"
    - "*.tfstate"
  
  # Severity levels to include
  severity_levels:
    - CRITICAL
    - HIGH
    - MEDIUM
    - LOW
  
  # Output formats
  output_formats:
    - json
    - text
  
  # Framework support
  frameworks:
    - terraform
  
  # Skip checks by ID (configured via whitelist)
  skip_checks: []
```

### Checkov Script Implementation (scripts/tools/run_terraform_security.sh)
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

### Checkov Processor Implementation (scripts/terraform_security_processor.py)
```python
#!/usr/bin/env python3
"""
Terraform Security Processor for SimpleSecCheck
Processes Checkov JSON results and generates HTML report sections
"""

import json
import os
import sys
from datetime import datetime

def process_checkov_results(results_dir):
    """Process Checkov JSON results and generate HTML sections"""
    
    checkov_json_path = os.path.join(results_dir, 'checkov.json')
    
    if not os.path.exists(checkov_json_path):
        return None
    
    try:
        with open(checkov_json_path, 'r') as f:
            checkov_data = json.load(f)
        
        # Generate HTML section
        html_content = generate_checkov_html(checkov_data)
        return html_content
        
    except Exception as e:
        print(f"Error processing Checkov results: {e}", file=sys.stderr)
        return None

def generate_checkov_html(checkov_data):
    """Generate HTML content for Checkov results"""
    
    html = []
    html.append('<div class="tool-section" id="checkov-section">')
    html.append('<h2>🔍 Checkov Terraform Security Scan</h2>')
    
    if 'results' in checkov_data and 'failed_checks' in checkov_data['results']:
        failed_checks = checkov_data['results']['failed_checks']
        
        if failed_checks:
            # Count vulnerabilities by severity
            severity_counts = {}
            for check in failed_checks:
                severity = check.get('check_result', {}).get('result', 'FAIL')
                check_name = check.get('check_name', 'unknown')
                if 'HIGH' in check_name or 'CRITICAL' in check_name:
                    severity_counts['HIGH'] = severity_counts.get('HIGH', 0) + 1
                elif 'MEDIUM' in check_name or 'LOW' in check_name:
                    severity_counts['MEDIUM'] = severity_counts.get('MEDIUM', 0) + 1
                else:
                    severity_counts['LOW'] = severity_counts.get('LOW', 0) + 1
            
            # Summary
            html.append('<div class="summary">')
            html.append('<h3>Summary</h3>')
            html.append('<ul>')
            for severity, count in severity_counts.items():
                html.append(f'<li><strong>{severity}</strong>: {count} issues</li>')
            html.append('</ul>')
            html.append('</div>')
            
            # Detailed issues
            html.append('<div class="issues">')
            html.append('<h3>Security Issues</h3>')
            
            for check in failed_checks:
                html.append('<div class="issue">')
                html.append(f'<h4>{check.get("check_name", "Unknown Issue")}</h4>')
                html.append(f'<p><strong>File:</strong> {check.get("file_path", "Unknown")}</p>')
                html.append(f'<p><strong>Resource:</strong> {check.get("resource", "Unknown")}</p>')
                if 'guideline' in check:
                    html.append(f'<p><strong>Guideline:</strong> {check["guideline"]}</p>')
                html.append('</div>')
            
            html.append('</div>')
        else:
            html.append('<p>No security issues found.</p>')
    else:
        html.append('<p>No security issues found.</p>')
    
    html.append('</div>')
    
    return '\n'.join(html)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 terraform_security_processor.py <results_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    html_content = process_checkov_results(results_dir)
    
    if html_content:
        print(html_content)
    else:
        print("No Checkov results to process")
```

## 17. Integration Points

### Main Orchestrator Updates (scripts/security-check.sh)
```bash
# Add Checkov environment variables
export TERRAFORM_SECURITY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/terraform-security/config.yaml"

# Add Checkov execution section
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "--- Orchestrating Terraform Security Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export TERRAFORM_SECURITY_CONFIG_PATH="$TERRAFORM_SECURITY_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_terraform_security.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_terraform_security.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_terraform_security.sh"; then
            log_message "run_terraform_security.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_terraform_security.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_terraform_security.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Terraform Security Scan Orchestration Finished ---"
fi
```

### HTML Report Generator Updates (scripts/generate-html-report.py)
```python
# Add Checkov processor import
from terraform_security_processor import process_checkov_results

# Add Checkov processing in report generation
def generate_html_report(results_dir):
    # ... existing code ...
    
    # Process Checkov results
    checkov_html = process_checkov_results(results_dir)
    if checkov_html:
        html_parts.append(checkov_html)
    
    # ... rest of function ...
```

## 18. References & Resources
- Checkov Documentation: https://www.checkov.io/
- Terraform Security Best Practices: https://www.terraform.io/docs/cli/security/
- Infrastructure Security Scanning: Industry standards

