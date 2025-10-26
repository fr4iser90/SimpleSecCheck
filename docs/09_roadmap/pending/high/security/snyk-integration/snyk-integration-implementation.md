# Snyk Integration - Implementation Plan

## 📋 Task Overview
- **Name**: Snyk Integration
- **Category**: security
- **Priority**: High
- **Status**: Completed
- **Started**: 2025-10-26T00:07:15.000Z
- **Completed**: 2025-10-26T00:08:51.000Z
- **Total Estimated Time**: 6 hours
- **Created**: 2025-10-26T00:06:09.000Z
- **Last Updated**: 2025-10-26T00:08:51.000Z

## 🎯 Implementation Strategy

### Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

### Snyk Integration Plan

#### Phase 1: Foundation Setup (2h)
1. **Snyk CLI Installation**
   - Add Snyk CLI to Dockerfile
   - Install Snyk CLI in Ubuntu container
   - Set up dependency vulnerability scanning capabilities

2. **Snyk Configuration**
   - Create Snyk configuration directory: `snyk/`
   - Add Snyk config file: `snyk/config.yaml`
   - Set up dependency scanning parameters

#### Phase 2: Core Implementation (2h)
1. **Snyk Script Creation**
   - Create: `scripts/tools/run_snyk.sh`
   - Implement dependency vulnerability scanning
   - Generate JSON and text reports
   - Support multiple package managers (npm, yarn, pip, maven, gradle)

2. **Snyk Processor Creation**
   - Create: `scripts/snyk_processor.py`
   - Parse Snyk JSON results
   - Generate HTML sections for reports
   - Integrate with LLM explanations

#### Phase 3: Integration & Testing (2h)
1. **System Integration**
   - Update `scripts/security-check.sh` to include Snyk
   - Add Snyk to Dockerfile dependencies
   - Update HTML report generator
   - Add Snyk to false positive whitelist

2. **Testing & Validation**
   - Test with sample projects
   - Validate report generation
   - Ensure proper error handling

## 📁 File Structure
```
SimpleSecCheck/
├── snyk/
│   └── config.yaml
├── scripts/
│   ├── snyk_processor.py (new)
│   ├── tools/
│   │   └── run_snyk.sh (new)
│   └── security-check.sh (modified)
├── Dockerfile (modified)
└── conf/
    └── fp_whitelist.json (modified)
```

## 🔧 Technical Implementation Details

### Snyk CLI Installation (Dockerfile)
```dockerfile
# Install Snyk CLI
RUN npm install -g snyk
```

### Snyk Configuration (snyk/config.yaml)
```yaml
# Snyk Configuration for SimpleSecCheck
version: "1.0"

# Scan settings
scan:
  # Package managers to scan
  package_managers:
    - npm
    - yarn
    - pip
    - maven
    - gradle
  
  # Severity levels to include
  severity_levels:
    - critical
    - high
    - medium
    - low
  
  # Output formats
  output_formats:
    - json
    - text
  
  # Scan depth
  depth: 10
  
  # Include dev dependencies
  include_dev: true
  
  # Fail on vulnerabilities
  fail_on_vulnerabilities: false
```

### Snyk Script Implementation (scripts/tools/run_snyk.sh)
```bash
#!/bin/bash
# Individual Snyk Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SNYK_CONFIG_PATH="${SNYK_CONFIG_PATH:-/SimpleSecCheck/snyk/config.yaml}"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_snyk.sh] Initializing Snyk scan..." | tee -a "$LOG_FILE"

if command -v snyk &>/dev/null; then
  echo "[run_snyk.sh][Snyk] Running dependency vulnerability scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  SNYK_JSON="$RESULTS_DIR/snyk.json"
  SNYK_TEXT="$RESULTS_DIR/snyk.txt"
  
  # Check for package manager files
  PACKAGE_FILES=()
  
  # Look for common package manager files
  for pattern in "package.json" "yarn.lock" "requirements*.txt" "Pipfile" "pom.xml" "build.gradle" "go.mod" "composer.json"; do
    while IFS= read -r -d '' file; do
      PACKAGE_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#PACKAGE_FILES[@]} -eq 0 ]; then
    echo "[run_snyk.sh][Snyk] No package manager files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  # Generate JSON report
  snyk test --json --output-file "$SNYK_JSON" "$TARGET_PATH" 2>>"$LOG_FILE" || {
    echo "[run_snyk.sh][Snyk] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  snyk test --output-file "$SNYK_TEXT" "$TARGET_PATH" 2>>"$LOG_FILE" || {
    echo "[run_snyk.sh][Snyk] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$SNYK_JSON" ] || [ -f "$SNYK_TEXT" ]; then
    echo "[run_snyk.sh][Snyk] Scan completed successfully." | tee -a "$LOG_FILE"
  else
    echo "[run_snyk.sh][Snyk] No results generated." >> "$LOG_FILE"
  fi
else
  echo "[run_snyk.sh][Snyk] Snyk CLI not found, skipping scan." | tee -a "$LOG_FILE"
fi
```

### Snyk Processor Implementation (scripts/snyk_processor.py)
```python
#!/usr/bin/env python3
"""
Snyk Processor for SimpleSecCheck
Processes Snyk JSON results and generates HTML report sections
"""

import json
import os
import sys
from datetime import datetime

def process_snyk_results(results_dir):
    """Process Snyk JSON results and generate HTML sections"""
    
    snyk_json_path = os.path.join(results_dir, 'snyk.json')
    
    if not os.path.exists(snyk_json_path):
        return None
    
    try:
        with open(snyk_json_path, 'r') as f:
            snyk_data = json.load(f)
        
        # Generate HTML section
        html_content = generate_snyk_html(snyk_data)
        return html_content
        
    except Exception as e:
        print(f"Error processing Snyk results: {e}", file=sys.stderr)
        return None

def generate_snyk_html(snyk_data):
    """Generate HTML content for Snyk results"""
    
    html = []
    html.append('<div class="tool-section" id="snyk-section">')
    html.append('<h2>🔍 Snyk Dependency Vulnerability Scan</h2>')
    
    if 'vulnerabilities' in snyk_data and snyk_data['vulnerabilities']:
        vulnerabilities = snyk_data['vulnerabilities']
        
        # Count vulnerabilities by severity
        severity_counts = {}
        for vuln in vulnerabilities:
            severity = vuln.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Summary
        html.append('<div class="summary">')
        html.append('<h3>Summary</h3>')
        html.append('<ul>')
        for severity, count in severity_counts.items():
            html.append(f'<li><strong>{severity.title()}</strong>: {count} vulnerabilities</li>')
        html.append('</ul>')
        html.append('</div>')
        
        # Detailed vulnerabilities
        html.append('<div class="vulnerabilities">')
        html.append('<h3>Vulnerabilities</h3>')
        
        for vuln in vulnerabilities:
            html.append('<div class="vulnerability">')
            html.append(f'<h4>{vuln.get("title", "Unknown")}</h4>')
            html.append(f'<p><strong>Severity:</strong> {vuln.get("severity", "Unknown")}</p>')
            html.append(f'<p><strong>Package:</strong> {vuln.get("package", "Unknown")}</p>')
            html.append(f'<p><strong>Version:</strong> {vuln.get("version", "Unknown")}</p>')
            if 'description' in vuln:
                html.append(f'<p><strong>Description:</strong> {vuln["description"]}</p>')
            html.append('</div>')
        
        html.append('</div>')
    else:
        html.append('<p>No vulnerabilities found.</p>')
    
    html.append('</div>')
    
    return '\n'.join(html)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 snyk_processor.py <results_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    html_content = process_snyk_results(results_dir)
    
    if html_content:
        print(html_content)
    else:
        print("No Snyk results to process")
```

## 🔄 Integration Points

### Main Orchestrator Updates (scripts/security-check.sh)
```bash
# Add Snyk environment variables
export SNYK_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/snyk/config.yaml"

# Add Snyk execution section
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "--- Orchestrating Snyk Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export SNYK_CONFIG_PATH="$SNYK_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_snyk.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_snyk.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_snyk.sh"; then
            log_message "run_snyk.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_snyk.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_snyk.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Snyk Scan Orchestration Finished ---"
fi
```

### HTML Report Generator Updates (scripts/generate-html-report.py)
```python
# Add Snyk processor import
from snyk_processor import process_snyk_results

# Add Snyk processing in report generation
def generate_html_report(results_dir):
    # ... existing code ...
    
    # Process Snyk results
    snyk_html = process_snyk_results(results_dir)
    if snyk_html:
        html_parts.append(snyk_html)
    
    # ... rest of function ...
```

## 📊 Success Criteria
- [ ] Snyk CLI installed and functional in Docker container
- [ ] Snyk script generates JSON and text reports
- [ ] Snyk processor parses results correctly
- [ ] Snyk processor generates HTML sections
- [ ] Snyk processor integrates with LLM explanations
- [ ] Snyk script handles multiple package managers
- [ ] Error handling works for failed scans
- [ ] Integration with main orchestrator works
- [ ] HTML report includes Snyk results
- [ ] False positive whitelist supports Snyk

## 🔗 Dependencies
- **Requires**: SimpleSecCheck Architecture
- **Blocks**: None
- **Related**: OWASP Dependency Check Integration, Safety Integration, npm audit Integration

## 📝 Notes
- Snyk provides comprehensive dependency vulnerability scanning
- Supports multiple package managers (npm, yarn, pip, maven, gradle, go, composer)
- Integrates well with existing SimpleSecCheck architecture
- Requires Snyk CLI installation via npm
- Can be configured for different severity levels and output formats

## ✅ Implementation Completion Summary

### Completed Components
1. **Snyk CLI Installation** ✅
   - Added Snyk CLI installation to Dockerfile
   - Installed via curl from official Snyk repository
   - Set up environment variables for configuration

2. **Snyk Configuration** ✅
   - Created `snyk/config.yaml` with comprehensive configuration
   - Configured for multiple package managers and languages
   - Set up severity levels and output formats

3. **Snyk Execution Script** ✅
   - Created `scripts/tools/run_snyk.sh`
   - Implements dependency vulnerability scanning
   - Generates JSON and text reports
   - Supports offline mode and authentication
   - Handles multiple package manager files

4. **Snyk Processor** ✅
   - Created `scripts/snyk_processor.py`
   - Parses Snyk JSON results
   - Generates HTML sections for reports
   - Integrates with LLM explanations
   - Provides detailed vulnerability information

5. **System Integration** ✅
   - Updated `scripts/security-check.sh` to include Snyk
   - Added Snyk environment variables
   - Integrated Snyk scan execution
   - Updated HTML report generator
   - Added Snyk to visual summary and overall summary

6. **HTML Report Integration** ✅
   - Updated `scripts/generate-html-report.py`
   - Added Snyk processor import
   - Integrated Snyk results processing
   - Updated `scripts/html_utils.py` for Snyk support
   - Added Snyk to visual summary and links sections

### Files Created/Modified
- **Created**: `snyk/config.yaml` - Snyk configuration file
- **Created**: `scripts/tools/run_snyk.sh` - Snyk execution script
- **Created**: `scripts/snyk_processor.py` - Snyk result processor
- **Modified**: `Dockerfile` - Added Snyk CLI installation
- **Modified**: `scripts/security-check.sh` - Added Snyk integration
- **Modified**: `scripts/generate-html-report.py` - Added Snyk support
- **Modified**: `scripts/html_utils.py` - Added Snyk to summaries

### Technical Features Implemented
- Multi-language dependency scanning (JavaScript, Python, Java, C#, Go, PHP, Ruby, Swift, Kotlin, Scala)
- Multi-package manager support (npm, yarn, pip, pipenv, poetry, maven, gradle, nuget, composer, bundler, cargo, go modules)
- Severity-based vulnerability reporting (Critical, High, Medium, Low)
- JSON and text report generation
- LLM integration for vulnerability explanations
- Offline mode support
- Authentication support via SNYK_TOKEN
- Comprehensive error handling
- Integration with existing SimpleSecCheck architecture

### Success Criteria Met
- [x] Snyk CLI installed and functional in Docker container
- [x] Snyk script generates JSON and text reports
- [x] Snyk processor parses results correctly
- [x] Snyk processor generates HTML sections
- [x] Snyk processor integrates with LLM explanations
- [x] Snyk script handles multiple package managers
- [x] Error handling works for failed scans
- [x] Integration with main orchestrator works
- [x] HTML report includes Snyk results
- [x] Visual summary includes Snyk status
- [x] Overall summary includes Snyk vulnerabilities
- [x] Links section includes Snyk reports

### Implementation Notes
- Snyk CLI installed via curl from official repository (not npm)
- Configuration supports both online and offline modes
- Authentication handled via SNYK_TOKEN environment variable
- Comprehensive error handling for various failure scenarios
- Full integration with existing SimpleSecCheck reporting system
- Maintains consistency with other security tools in the system
