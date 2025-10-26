# Bandit Integration - Implementation Plan

## 1. Project Overview
- **Feature/Component Name**: Bandit Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Static Application Security Testing (SAST) for Python applications
- **Created**: 2025-10-26T08:05:28.000Z
- **Last Updated**: 2025-10-26T08:05:28.000Z

## 2. Technical Requirements
- **Tech Stack**: Python, Bash, Bandit CLI
- **Architecture Pattern**: Modular tool integration
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: HTML report generation
- **Backend Changes**: Bandit processor, script creation

## 3. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py, snyk_processor.py, sonarqube_processor.py, terraform_security_processor.py, trufflehog_processor.py, wapiti_processor.py, nikto_processor.py, zap_processor.py, eslint_processor.py, burp_processor.py, brakeman_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

## 4. Bandit Integration Details

### 4.1 Bandit Overview
- **Type**: Static Application Security Testing (SAST) for Python applications
- **Purpose**: Analyzes Python code for security vulnerabilities
- **Output**: JSON format with security findings
- **Common Findings**: SQL injection, shell injection, weak cryptographic functions, hardcoded secrets, insecure random number generation

### 4.2 Integration Strategy
- Install Bandit as Python package in Docker container
- Use CLI mode for automated scanning
- Generate JSON reports for processing
- Follow existing SAST tool patterns (Semgrep, CodeQL, Safety)
- Scan Python files for security issues

## 5. Implementation Phases

#### Phase 1: Foundation Setup (2 hours)
- [ ] Bandit Installation: Install Bandit package in Dockerfile
- [ ] Bandit Configuration: Create bandit/ directory with config.yaml
- [ ] Environment Setup: Set up Bandit scanning parameters

#### Phase 2: Core Implementation (2 hours)
- [ ] Bandit Script Creation: Create scripts/tools/run_bandit.sh
- [ ] Bandit Processor Creation: Create scripts/bandit_processor.py
- [ ] Report Generation: Generate JSON and text reports
- [ ] LLM Integration: Integrate with LLM explanations

#### Phase 3: Integration & Testing (2 hours)
- [ ] System Integration: Update scripts/security-check.sh
- [ ] Dockerfile Updates: Add Bandit installation to Dockerfile
- [ ] HTML Report Updates: Update generate-html-report.py
- [ ] Testing: Test with sample Python projects

## 6. File Impact Analysis
#### Files to Modify:
- [ ] `Dockerfile` - Add Bandit package installation
- [ ] `scripts/security-check.sh` - Add Bandit orchestration
- [ ] `scripts/generate-html-report.py` - Add Bandit report integration
- [ ] `conf/fp_whitelist.json` - Add Bandit false positive handling

#### Files to Create:
- [ ] `bandit/config.yaml` - Bandit configuration
- [ ] `scripts/tools/run_bandit.sh` - Bandit execution script
- [ ] `scripts/bandit_processor.py` - Bandit result processor

#### Files to Delete:
- [ ] None

## 7. Code Standards & Patterns
- **Coding Style**: Follow existing Python and Bash patterns
- **Naming Conventions**: snake_case for files, consistent with existing tools
- **Error Handling**: Handle errors appropriately with logging
- **Logging**: Use existing log_message function
- **Testing**: Manual testing with sample Python applications
- **Documentation**: Inline comments and README updates

## 8. Security Considerations
- [ ] Validate Python project structure
- [ ] Sanitize report data in output
- [ ] Handle sensitive code snippets in reports
- [ ] Configure appropriate Bandit checks
- [ ] Manage scan timeouts for large applications

## 9. Performance Requirements
- **Response Time**: < 2 minutes for standard Python application
- **Memory Usage**: < 500MB additional memory
- **Scan Scope**: Python-specific security checks
- **Caching Strategy**: Cache scan results

## 10. Testing Strategy
#### Unit Tests:
- [ ] Test Bandit processor functions
- [ ] Test configuration parsing
- [ ] Test result formatting

#### Integration Tests:
- [ ] Test with sample Python applications
- [ ] Test report generation
- [ ] Test error handling scenarios

#### E2E Tests:
- [ ] Test complete scan workflow
- [ ] Test HTML report integration
- [ ] Test false positive handling

## 11. Documentation Requirements
- [ ] Update README with Bandit information
- [ ] Document Bandit configuration options
- [ ] Add troubleshooting guide
- [ ] Update CHANGELOG

## 12. Deployment Checklist
- [ ] Verify Bandit installation in Docker
- [ ] Test configuration file
- [ ] Validate script permissions
- [ ] Test report generation
- [ ] Verify error handling

## 13. Success Criteria
- [ ] Bandit successfully scans Python applications
- [ ] Results are properly parsed and formatted
- [ ] HTML reports include Bandit findings
- [ ] Error handling works correctly
- [ ] Performance meets requirements
- [ ] Documentation is complete

## 14. Risk Assessment
- [ ] Python version compatibility
- [ ] Performance impact on scan time
- [ ] False positive management
- [ ] Scan timeout for large applications

## 15. AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/bandit-integration/bandit-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

## 16. References & Resources
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Bandit GitHub](https://github.com/PyCQA/bandit)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- SimpleSecCheck Architecture
- Existing SAST Tool Integration Patterns

## 17. Bandit-Specific Configuration
### Common Vulnerability Checks
- SQL injection vulnerabilities
- Shell injection via subprocess
- Hardcoded secrets and passwords
- Weak cryptographic functions
- Insecure random number generation
- XML vulnerabilities (XXE)
- YAML vulnerabilities
- Pickle deserialization issues
- Insecure SSL/TLS configuration
- Debug statements left in code

## 18. Integration Details
### Python File Detection
- Detect `.py` files in project
- Parse Python application structure
- Run Bandit scan on detected Python projects

### Report Format
- JSON output for machine-readable results
- Text output for human-readable summaries
- HTML integration for web-based reports

## 19. Technical Implementation Details

### Updated Dockerfile
```dockerfile
# Install Bandit CLI
RUN pip3 install bandit[toml]

# Set Bandit environment variables
ENV BANDIT_CONFIG_PATH=/SimpleSecCheck/bandit/config.yaml
```

### Updated security-check.sh Orchestrator
```bash
# Only run Bandit for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_bandit.sh
    log_message "--- Orchestrating Bandit Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export BANDIT_CONFIG_PATH="$BASE_PROJECT_DIR/bandit/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_bandit.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_bandit.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_bandit.sh"; then
            log_message "run_bandit.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_bandit.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_bandit.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Bandit Scan Orchestration Finished ---"
else
    log_message "--- Skipping Bandit Scan (Website scan mode) ---"
fi
```

### Bandit Script Template
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

### Bandit Processor Template
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

### Updated HTML Report Generator
```python
# Add to generate-html-report.py imports
from scripts.bandit_processor import bandit_summary, generate_bandit_html_section

# Add to main report generation
def generate_html_report(results_dir):
    # ... existing code ...
    
    # Process Bandit results
    bandit_json_file = os.path.join(results_dir, 'bandit.json')
    bandit_findings = []
    if os.path.exists(bandit_json_file):
        try:
            bandit_data = load_bandit_results(bandit_json_file)
            if bandit_data:
                bandit_findings = bandit_summary(bandit_data)
        except Exception as e:
            debug(f"Error processing Bandit results: {e}")
    
    # ... existing code ...
    
    # Add Bandit section to HTML
    html_content += generate_bandit_html_section(bandit_findings)
    
    # ... existing code ...
```

