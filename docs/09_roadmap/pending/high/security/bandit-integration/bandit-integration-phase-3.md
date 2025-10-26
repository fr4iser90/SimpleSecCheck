# Bandit Integration – Phase 3: Integration & Testing

## Overview
This phase completes Bandit integration by updating the orchestrator, HTML report generator, and performing complete testing.

## Objectives
- [ ] Update scripts/security-check.sh to include Bandit
- [ ] Update scripts/generate-html-report.py to process Bandit results
- [ ] Test complete Bandit integration
- [ ] Verify HTML report generation
- [ ] Validate error handling

## Deliverables
- File: `scripts/security-check.sh` - Updated with Bandit orchestration
- File: `scripts/generate-html-report.py` - Updated with Bandit processing
- File: `conf/fp_whitelist.json` - Updated with Bandit false positive handling
- Test results: Bandit integration fully validated

## Dependencies
- Requires: Phase 2 completion (Script and processor created)
- Blocks: None

## Estimated Time
2 hours

## Success Criteria
- [ ] Bandit orchestration added to security-check.sh
- [ ] Bandit processor integrated with HTML generator
- [ ] Bandit results display correctly in HTML reports
- [ ] Error handling works for failed scans
- [ ] Complete integration tested with sample projects

## Technical Details

### Orchestrator Updates
Add the following section to `scripts/security-check.sh` after the Brakeman section (around line 600):

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

### Environment Variable Updates
Add to the configuration section at the top of `scripts/security-check.sh`:

```bash
export BANDIT_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/bandit/config.yaml"
```

Add to the log output section:

```bash
log_message "Bandit Config Path (BANDIT_CONFIG_PATH_IN_CONTAINER): $BANDIT_CONFIG_PATH_IN_CONTAINER"
```

### HTML Report Generator Updates
Add to imports section in `scripts/generate-html-report.py`:

```python
from scripts.bandit_processor import bandit_summary, generate_bandit_html_section
```

Add to the main report generation function:

```python
# Process Bandit results
bandit_json_file = os.path.join(results_dir, 'bandit.json')
bandit_findings = []
if os.path.exists(bandit_json_file):
    try:
        with open(bandit_json_file, 'r') as f:
            bandit_data = json.load(f)
            bandit_findings = bandit_summary(bandit_data)
    except Exception as e:
        debug(f"Error processing Bandit results: {e}")

# ... in HTML generation section ...
html_content += generate_bandit_html_section(bandit_findings)
```

### False Positive Whitelist
Update `conf/fp_whitelist.json` to include Bandit false positive handling:

```json
{
  "bandit": {
    "enabled": true,
    "default_action": "include",
    "exclusions": []
  }
}
```

## Testing Strategy

### Unit Tests
1. Test Bandit processor functions independently
2. Test JSON parsing with sample Bandit output
3. Test HTML generation with various finding types
4. Test error handling scenarios

### Integration Tests
1. Test complete Bandit orchestration with orchestrator
2. Test HTML report generation with Bandit results
3. Test multiple scan types (code vs website)
4. Test error handling and recovery

### End-to-End Tests
1. Test Bandit scanning with Python project
2. Test with project containing no Python files
3. Test with mixed-language projects
4. Verify HTML report content and formatting

## Validation Steps

### 1. Orchestrator Integration
- [ ] Verify Bandit orchestration section added correctly
- [ ] Test Bandit execution in orchestrator flow
- [ ] Verify log messages are correct
- [ ] Test error handling for missing script

### 2. HTML Report Integration
- [ ] Verify Bandit processor import works
- [ ] Test HTML section generation
- [ ] Verify Bandit results display in HTML
- [ ] Test empty results handling

### 3. Complete Workflow
- [ ] Run full scan with Python project
- [ ] Verify all reports are generated
- [ ] Check HTML report includes Bandit section
- [ ] Verify error handling works properly

### 4. Edge Cases
- [ ] Test with project having no Python files
- [ ] Test with Python file containing no issues
- [ ] Test with Python file containing various severity issues
- [ ] Test timeout handling for large projects

## Deployment Checklist

### Pre-Deployment
- [ ] Verify Bandit installation in Docker image
- [ ] Confirm configuration file exists
- [ ] Test script permissions
- [ ] Validate processor functionality

### Deployment
- [ ] Build new Docker image
- [ ] Test Docker image with sample project
- [ ] Verify all integrations work
- [ ] Check logging output

### Post-Deployment
- [ ] Monitor log files for errors
- [ ] Verify HTML reports are generated correctly
- [ ] Test with various Python projects
- [ ] Update documentation

## Rollback Plan
If issues are found:
1. Remove Bandit orchestration section from security-check.sh
2. Remove Bandit processor import from generate-html-report.py
3. Remove Bandit environment variables
4. Revert Dockerfile changes if needed
5. Rebuild Docker image

## Success Criteria Verification

### Functional Verification
- [ ] Bandit successfully scans Python applications
- [ ] Results are properly parsed and formatted
- [ ] HTML reports include Bandit findings
- [ ] Error handling works correctly
- [ ] Performance meets requirements

### Quality Verification
- [ ] Code follows project standards
- [ ] Logging is comprehensive
- [ ] Error messages are clear
- [ ] Documentation is complete
- [ ] No regressions in other tools

## Notes
- Bandit is a SAST tool for Python code security
- Integration follows existing tool patterns
- HTML reports include severity and confidence information
- Error handling ensures graceful degradation

## Validation Marker
✅ Phase 3 files validated and created: 2025-10-26T08:05:28.000Z

