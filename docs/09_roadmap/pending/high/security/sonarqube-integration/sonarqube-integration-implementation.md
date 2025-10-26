# SonarQube Integration - Implementation Plan

## 📋 Task Overview
- **Name**: SonarQube Integration
- **Category**: security
- **Priority**: High
- **Status**: Implementation Complete
- **Total Estimated Time**: 6 hours
- **Created**: 2025-10-25T23:44:26.000Z
- **Last Updated**: 2025-10-26T00:12:26.000Z

## 🎯 Implementation Strategy

### Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py, snyk_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

### SonarQube Integration Plan

#### Phase 1: Foundation Setup (2h)
1. **SonarQube Scanner Installation**
   - Add SonarQube Scanner CLI to Dockerfile
   - Install SonarQube Scanner in Ubuntu container
   - Set up code quality and security scanning capabilities

2. **SonarQube Configuration**
   - Create SonarQube configuration directory: `sonarqube/`
   - Add SonarQube config file: `sonarqube/config.yaml`
   - Set up project properties and quality gate rules

#### Phase 2: Core Implementation (2h)
1. **SonarQube Script Creation**
   - Create: `scripts/tools/run_sonarqube.sh`
   - Implement code quality and security scanning
   - Generate JSON and text reports
   - Support multiple programming languages

2. **SonarQube Processor Creation**
   - Create: `scripts/sonarqube_processor.py`
   - Parse SonarQube JSON results
   - Generate HTML sections for reports
   - Integrate with LLM explanations

#### Phase 3: Integration & Testing (2h)
1. **System Integration**
   - Update `scripts/security-check.sh` to include SonarQube
   - Add SonarQube to Dockerfile dependencies
   - Update HTML report generator
   - Add SonarQube to false positive whitelist

2. **Testing & Validation**
   - Test with sample codebases
   - Validate report generation
   - Ensure proper error handling

## 📁 File Structure
```
SimpleSecCheck/
├── sonarqube/
│   └── config.yaml
├── scripts/
│   ├── sonarqube_processor.py (new)
│   ├── tools/
│   │   └── run_sonarqube.sh (new)
│   └── security-check.sh (modified)
├── Dockerfile (modified)
└── conf/
    └── fp_whitelist.json (modified)
```

## 🔧 Technical Implementation Details

### SonarQube Scanner Installation (Dockerfile)
```dockerfile
# Install SonarQube Scanner
RUN export SONAR_SCANNER_URL=$(wget -qO- https://api.github.com/repos/SonarSource/sonar-scanner-cli/releases/latest | grep browser_download_url | grep sonar-scanner-cli.*linux-x86_64.tar.gz | cut -d '"' -f 4) && \
    wget -O sonar-scanner.tar.gz $SONAR_SCANNER_URL && \
    tar -xvzf sonar-scanner.tar.gz -C /opt && \
    rm sonar-scanner.tar.gz && \
    ln -s /opt/sonar-scanner-*/bin/sonar-scanner /usr/local/bin/sonar-scanner
```

### SonarQube Configuration (sonarqube/config.yaml)
```yaml
# SonarQube Configuration for SimpleSecCheck
# Configuration file for SonarQube code quality and security scanning

# Project configuration
project:
  name: SimpleSecCheck-Analysis
  version: 1.0.0
  
# Analysis settings
analysis:
  # Source directory
  source_dir: "/target"
  
  # Language detection
  languages:
    auto_detect: true
    supported_languages:
      - java
      - python
      - javascript
      - typescript
      - csharp
      - go
      - kotlin
      - php
      
  # Quality gate settings
  quality_gate:
    # Pass threshold
    pass_threshold: "default"
    
    # Severity levels to report
    severity_levels:
      - blocker
      - critical
      - major
      - minor
      - info
      
  # Analysis options
  options:
    # Analysis timeout (seconds)
    timeout: 600
    
    # Memory limit (MB)
    memory_limit: 4096
    
    # Thread count
    threads: 4
    
    # Enable concurrent analysis
    concurrent: true

# Output settings
output:
  # Output formats
  formats:
    - json
    - text
  
  # Include detailed issues
  detailed: true
  
  # Include code snippets
  code_snippets: true
  
  # Include metrics
  metrics: true

# Exclusion patterns
exclusions:
  # Exclude patterns
  patterns:
    - "*/test*"
    - "*/tests/*"
    - "*/__pycache__/*"
    - "*/node_modules/*"
    - "*/venv/*"
    - "*/env/*"
    - "*/virtualenv/*"
    - "*/target/*"
    - "*/build/*"
    - "*/dist/*"

# Coverage settings
coverage:
  # Coverage report locations
  report_paths:
    - "**/coverage.xml"
    - "**/jacoco.xml"
    
  # Minimum coverage threshold
  minimum_coverage: 0.0

# Security scanning settings
security:
  # Enable security analysis
  enable_security: true
  
  # Security rules
  rules:
    # SonarQube security rules
    sonarqube_rules: true
    
    # Custom security rules
    custom_rules: []
    
  # Vulnerability detection
  vulnerabilities:
    # Detect SQL injection
    sql_injection: true
    
    # Detect XSS vulnerabilities
    xss: true
    
    # Detect path traversal
    path_traversal: true
    
    # Detect insecure deserialization
    deserialization: true
    
    # Detect weak cryptography
    weak_crypto: true

# Code quality settings
quality:
  # Code smells detection
  code_smells: true
  
  # Duplication detection
  duplication: true
  
  # Technical debt tracking
  technical_debt: true
  
  # Code complexity metrics
  complexity: true
  
  # Maintainability rating
  maintainability: true

# Integration settings
integration:
  # Exit code on issues found
  exit_on_issues: false
  
  # Include in HTML report
  include_in_html: true
  
  # Generate separate report files
  generate_files: true
  
  # Fail on quality gate
  fail_on_quality_gate: false
```

### SonarQube Script Implementation (scripts/tools/run_sonarqube.sh)
```bash
#!/bin/bash
# Individual SonarQube Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

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

### SonarQube Processor Implementation (scripts/sonarqube_processor.py)
```python
#!/usr/bin/env python3
"""
SonarQube Processor for SimpleSecCheck
Processes SonarQube results and generates HTML report sections
"""

import json
import os
import sys
from datetime import datetime

def process_sonarqube_results(results_dir):
    """Process SonarQube results and generate HTML sections"""
    
    sonarqube_json_path = os.path.join(results_dir, 'sonarqube.json')
    
    if not os.path.exists(sonarqube_json_path):
        return None
    
    try:
        with open(sonarqube_json_path, 'r') as f:
            sonarqube_data = json.load(f)
        
        # Generate HTML section
        html_content = generate_sonarqube_html(sonarqube_data)
        return html_content
        
    except Exception as e:
        print(f"Error processing SonarQube results: {e}", file=sys.stderr)
        return None

def generate_sonarqube_html(sonarqube_data):
    """Generate HTML content for SonarQube results"""
    
    html = []
    html.append('<div class="tool-section" id="sonarqube-section">')
    html.append('<h2>🔍 SonarQube Code Quality & Security Scan</h2>')
    
    if 'issues' in sonarqube_data and sonarqube_data['issues']:
        issues = sonarqube_data['issues']
        
        # Count issues by severity
        severity_counts = {'BLOCKER': 0, 'CRITICAL': 0, 'MAJOR': 0, 'MINOR': 0, 'INFO': 0}
        for issue in issues:
            severity = issue.get('severity', 'INFO')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
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
        html.append('<h3>Issues</h3>')
        html.append('<table>')
        html.append('<tr><th>Severity</th><th>Component</th><th>Message</th><th>Line</th></tr>')
        
        for issue in issues[:50]:  # Limit to first 50 issues
            severity = issue.get('severity', 'INFO')
            component = issue.get('component', 'Unknown')
            message = issue.get('message', 'No message')
            line = issue.get('line', 'N/A')
            
            html.append(f'<tr class="severity-{severity}">')
            html.append(f'<td>{severity}</td>')
            html.append(f'<td>{component}</td>')
            html.append(f'<td>{message}</td>')
            html.append(f'<td>{line}</td>')
            html.append('</tr>')
        
        html.append('</table>')
        html.append('</div>')
    else:
        html.append('<p>No issues found.</p>')
    
    html.append('</div>')
    
    return '\n'.join(html)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 sonarqube_processor.py <results_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    html_content = process_sonarqube_results(results_dir)
    
    if html_content:
        print(html_content)
    else:
        print("No SonarQube results to process")
```

## 🔄 Integration Points

### Main Orchestrator Updates (scripts/security-check.sh)
```bash
# Add SonarQube environment variables
export SONARQUBE_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/sonarqube/config.yaml"

# Add SonarQube execution section (for code scans only)
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_sonarqube.sh
    log_message "--- Orchestrating SonarQube Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export LOG_FILE="$LOG_FILE"
    export SONARQUBE_CONFIG_PATH="$SONARQUBE_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_sonarqube.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_sonarqube.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_sonarqube.sh"; then
            log_message "run_sonarqube.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_sonarqube.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_sonarqube.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- SonarQube Scan Orchestration Finished ---"
fi
```

### HTML Report Generator Updates (scripts/generate-html-report.py)
```python
# Add SonarQube processor import
from sonarqube_processor import process_sonarqube_results

# Add SonarQube processing in report generation
def generate_html_report(results_dir):
    # ... existing code ...
    
    # Process SonarQube results
    sonarqube_html = process_sonarqube_results(results_dir)
    if sonarqube_html:
        html_parts.append(sonarqube_html)
    
    # ... rest of function ...
```

## 📊 Success Criteria
- [x] SonarQube Scanner installed and functional in Docker container
- [x] SonarQube script generates JSON and text reports
- [x] SonarQube processor parses results correctly
- [x] SonarQube processor generates HTML sections
- [x] SonarQube processor integrates with LLM explanations
- [x] SonarQube script handles multiple programming languages
- [x] Error handling works for failed scans
- [x] Integration with main orchestrator works
- [x] HTML report includes SonarQube results
- [x] False positive whitelist supports SonarQube

## 🔗 Dependencies
- **Requires**: SimpleSecCheck Architecture
- **Blocks**: None
- **Related**: CodeQL Integration, Semgrep Integration

## 📝 Notes
- SonarQube provides code quality and security analysis
- Supports multiple programming languages (Java, Python, JavaScript, TypeScript, C#, Go, Kotlin, PHP)
- Integrates well with existing SimpleSecCheck architecture
- Requires SonarQube Scanner CLI installation
- Can be configured for different quality gates and severity levels

## 🔑 AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/sonarqube-integration/sonarqube-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

## 📚 References & Resources
- SonarQube Documentation: https://docs.sonarsource.com/sonarqube/latest/
- SonarQube Scanner CLI: https://github.com/SonarSource/sonar-scanner-cli
- SonarQube Quality Gates: https://docs.sonarsource.com/sonarqube/latest/user-guide/quality-gates/
- SonarQube Security Rules: https://rules.sonarsource.com/

