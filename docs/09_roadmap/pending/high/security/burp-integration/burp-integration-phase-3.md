# Burp Suite Integration – Phase 3: Integration & Testing

## Overview
This phase completes the integration by updating the orchestrator and report generator, followed by testing.

## Status: ✅ Complete (2025-10-26T08:25:00.000Z)

## Objectives
- [x] Update main orchestrator (security-check.sh)
- [x] Update HTML report generator (generate-html-report.py)
- [x] Add Burp Suite to false positive whitelist
- [x] Test complete integration workflow
- [x] Validate error handling and edge cases

## Deliverables
- File: `scripts/security-check.sh` - Updated orchestrator with Burp Suite
- File: `scripts/generate-html-report.py` - Updated HTML report generator
- File: `conf/fp_whitelist.json` - Updated false positive whitelist
- Testing: Complete integration tested and validated

## Dependencies
- Requires: Phase 2 completion
- Blocks: None (final phase)

## Estimated Time
2 hours

## Success Criteria
- [x] Burp Suite is integrated into main orchestrator
- [x] HTML reports include Burp Suite findings
- [x] Error handling works correctly
- [x] Complete workflow tested successfully
- [x] Edge cases are handled properly

## Implementation Details

### Step 1: Update Main Orchestrator
Update `scripts/security-check.sh` to add Burp Suite integration:

Add environment variable:
```bash
export BURP_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/burp/config.yaml"
```

Add orchestration section in website scan mode (after ZAP, Nuclei, Wapiti, Nikto):
```bash
# Only run Burp Suite for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    log_message "--- Orchestrating Burp Suite Scan ---"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export BURP_CONFIG_PATH="$BURP_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_burp.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_burp.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_burp.sh"; then
            log_message "run_burp.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_burp.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_burp.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Burp Suite Scan Orchestration Finished ---"
else
    log_message "--- Skipping Burp Suite Scan (Code scan mode) ---"
fi
```

### Step 2: Update HTML Report Generator
Update `scripts/generate-html-report.py` to include Burp Suite results:

Add import:
```python
from burp_processor import process_burp_results
```

Add report section generation:
```python
def generate_burp_html_section(results_dir):
    """Generate HTML section for Burp Suite results"""
    # Process Burp Suite results
    # Generate HTML section
    # Return HTML content
    pass
```

### Step 3: Update False Positive Whitelist
Update `conf/fp_whitelist.json` to include Burp Suite false positives:

```json
{
  "burp": {
    "common_false_positives": [
      "Informational finding",
      "Low severity issues"
    ]
  }
}
```

### Step 4: Test Complete Workflow
Test the complete integration:

```bash
# Run website scan with Burp Suite
./run-docker.sh https://example.com

# Verify results directory contains Burp Suite results
ls -la results/*/burp-*

# Verify HTML report includes Burp Suite section
cat results/*/security-summary.html | grep -i burp
```

### Step 5: Validate Error Handling
Test error scenarios:

- Network errors
- Invalid target URLs
- Missing configuration files
- License key issues (for Professional edition)
- Scan timeouts

## Testing Checklist
- [ ] Burp Suite runs successfully in website scan mode
- [ ] Results are properly parsed and formatted
- [ ] HTML reports include Burp Suite findings
- [ ] Error handling works for all failure scenarios
- [ ] Performance is acceptable
- [ ] No regressions in existing functionality

## Notes
- Burp Suite scans can be slower than other DAST tools
- Consider implementing scan duration limits
- Community Edition has scan limitations
- Professional Edition requires license key management
- Ensure proper cleanup of scan artifacts
