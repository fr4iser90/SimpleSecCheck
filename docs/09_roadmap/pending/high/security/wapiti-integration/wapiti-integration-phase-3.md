# Wapiti Integration – Phase 3: Integration & Testing

## Overview
Integrate Wapiti into the main orchestrator and complete testing. This phase finalizes the integration and ensures everything works correctly.

## Objectives
- [x] Update main security-check.sh orchestrator
- [x] Update Dockerfile with Wapiti dependencies
- [x] Update HTML report generator
- [x] Test complete integration

## Deliverables
- [x] File: `scripts/security-check.sh` - Updated with Wapiti orchestration
- [x] File: `Dockerfile` - Updated with Wapiti installation
- [x] File: `scripts/generate-html-report.py` - Updated with Wapiti section
- [x] Test results and validation report

## Dependencies
- Requires: Phase 2 completion (Core implementation)
- Blocks: None (Final phase)

## Estimated Time
2 hours

## Success Criteria
- [ ] Wapiti integrated into security-check.sh
- [ ] Dockerfile includes Wapiti installation
- [ ] HTML report includes Wapiti findings
- [ ] All tests pass successfully
- [ ] Integration works end-to-end

## Technical Details

### 3.1 Main Orchestrator Integration
Update `scripts/security-check.sh`:

Add Wapiti configuration path:
```bash
export WAPITI_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/wapiti/config.yaml"
```

Add Wapiti orchestration for website scans:
```bash
# Only run Wapiti for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    log_message "--- Orchestrating Wapiti Scan ---"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export WAPITI_CONFIG_PATH="$WAPITI_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_wapiti.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_wapiti.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_wapiti.sh"; then
            log_message "run_wapiti.sh completed successfully."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_wapiti.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_wapiti.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Wapiti Scan Orchestration Finished ---"
else
    log_message "--- Skipping Wapiti Scan (Code scan mode) ---"
fi
```

### 3.2 Dockerfile Updates
Add Wapiti installation to `Dockerfile`:
```dockerfile
# Install Wapiti CLI
RUN pip3 install wapiti3
```

Add Wapiti environment variables:
```dockerfile
# Set Wapiti environment variables
ENV WAPITI_CONFIG_PATH=/SimpleSecCheck/wapiti/config.yaml
```

### 3.3 HTML Report Updates
Update `scripts/generate-html-report.py`:

Import Wapiti processor:
```python
from scripts import wapiti_processor
```

Add Wapiti section to report:
```python
# Wapiti results
wapiti_json_path = Path(results_dir) / "wapiti.json"
if wapiti_json_path.exists():
    try:
        with open(wapiti_json_path, 'r') as f:
            wapiti_data = json.load(f)
        wapiti_findings = wapiti_processor.wapiti_summary(wapiti_data)
        wapiti_html = wapiti_processor.generate_wapiti_html_section(wapiti_findings)
        sections.append(wapiti_html)
    except Exception as e:
        debug(f"Error processing Wapiti results: {e}")
```

### 3.4 Testing & Validation
Test checklist:
- [ ] Run security-check.sh with SCAN_TYPE=website
- [ ] Verify Wapiti runs against target
- [ ] Check wapiti.json and wapiti.txt are created
- [ ] Verify HTML report includes Wapiti section
- [ ] Check log file for Wapiti entries
- [ ] Test error handling with invalid target
- [ ] Test with sample web application

## Notes
- Wapiti is a DAST tool for website scans only
- Follow same pattern as ZAP and Nuclei integration
- Ensure proper error handling and logging
- Test with real web applications
- Verify HTML report generation works correctly

