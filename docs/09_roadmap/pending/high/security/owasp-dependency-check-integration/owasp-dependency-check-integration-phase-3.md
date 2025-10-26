# OWASP Dependency Check Integration – Phase 3: Integration & Testing

## Overview
Integrate OWASP Dependency Check with SimpleSecCheck orchestrator and perform complete testing and validation.

## Objectives
- [ ] Integrate OWASP Dependency Check with main orchestrator
- [ ] Update HTML report generator to include OWASP Dependency Check results
- [ ] Add OWASP Dependency Check to false positive whitelist
- [ ] Perform complete end-to-end testing

## Deliverables
- File: `scripts/security-check.sh` - Updated orchestrator
- File: `scripts/generate-html-report.py` - Updated HTML generator
- File: `conf/fp_whitelist.json` - Updated whitelist
- Test: Complete integration testing
- Test: End-to-end workflow validation

## Dependencies
- Requires: Phase 2 completion (core implementation)
- Blocks: Task completion

## Estimated Time
2 hours

## Detailed Tasks

### Task 3.1: Orchestrator Integration (1 hour)
- [ ] **3.1.1** Update `scripts/security-check.sh` to include OWASP Dependency Check
- [ ] **3.1.2** Add OWASP Dependency Check environment variables
- [ ] **3.1.3** Add OWASP Dependency Check execution to code scan flow
- [ ] **3.1.4** Test orchestrator integration

### Task 3.2: Report Integration & Testing (1 hour)
- [ ] **3.2.1** Update `scripts/generate-html-report.py` to include OWASP Dependency Check
- [ ] **3.2.2** Add OWASP Dependency Check to false positive whitelist
- [ ] **3.2.3** Test complete HTML report generation
- [ ] **3.2.4** Perform end-to-end testing

## Technical Implementation Details

### Updated security-check.sh Orchestrator
```bash
# Add OWASP Dependency Check environment variables
export OWASP_DEPENDENCY_CHECK_CONFIG_PATH="$BASE_PROJECT_DIR/owasp-dependency-check/config.yaml"

# Add OWASP Dependency Check to code scan flow
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_owasp_dependency_check.sh
    log_message "--- Orchestrating OWASP Dependency Check Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export OWASP_DEPENDENCY_CHECK_CONFIG_PATH="$OWASP_DEPENDENCY_CHECK_CONFIG_PATH"
    if [ -f "$TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh"; then
            log_message "run_owasp_dependency_check.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_owasp_dependency_check.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- OWASP Dependency Check Scan Orchestration Finished ---"
else
    log_message "--- Skipping OWASP Dependency Check Scan (Website scan mode) ---"
fi
```

### Updated HTML Report Generator
```python
# Add OWASP Dependency Check imports
from scripts.owasp_dependency_check_processor import owasp_dependency_check_summary, generate_owasp_dependency_check_html_section

# Add OWASP Dependency Check file paths
owasp_json_path = os.path.join(RESULTS_DIR, 'owasp-dependency-check.json')

# Add OWASP Dependency Check processing
owasp_json = read_json(owasp_json_path)
owasp_vulns = owasp_dependency_check_summary(owasp_json)

# Add OWASP Dependency Check to visual summary
f.write(generate_visual_summary_section(zap_alerts.get('summary', zap_alerts), semgrep_findings, trivy_vulns, codeql_findings, nuclei_findings, owasp_vulns))

# Add OWASP Dependency Check section
f.write(generate_owasp_dependency_check_html_section(owasp_vulns))
```

### Updated False Positive Whitelist
```json
{
  "owasp_dependency_check": {
    "common_false_positives": [
      {
        "pattern": ".*test.*",
        "reason": "Test dependencies",
        "severity": "LOW"
      },
      {
        "pattern": ".*dev.*",
        "reason": "Development dependencies",
        "severity": "LOW"
      }
    ]
  }
}
```

## Success Criteria
- [ ] OWASP Dependency Check integrates with orchestrator
- [ ] HTML reports include OWASP Dependency Check results
- [ ] False positive whitelist includes OWASP Dependency Check patterns
- [ ] Complete end-to-end workflow works
- [ ] Error handling works in integrated environment
- [ ] Performance is acceptable with other tools

## Testing Checklist
- [ ] Test orchestrator with OWASP Dependency Check enabled
- [ ] Verify HTML report includes OWASP Dependency Check section
- [ ] Test false positive whitelist functionality
- [ ] Test error scenarios in integrated environment
- [ ] Verify parallel execution with other tools
- [ ] Test with different project types
- [ ] Validate complete scan workflow
- [ ] Check log output and error reporting

## Integration Validation
- [ ] OWASP Dependency Check runs in parallel with other tools
- [ ] Results are properly integrated into HTML report
- [ ] Error handling doesn't break other tools
- [ ] Performance impact is minimal
- [ ] Configuration is properly loaded
- [ ] Environment variables are correctly set
