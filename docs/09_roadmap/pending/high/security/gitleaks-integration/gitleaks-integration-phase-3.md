# GitLeaks Integration – Phase 3: Integration & Testing

## Overview
Integrate GitLeaks into the main security check orchestrator and HTML report generator, then test the complete integration.

## Objectives
- [ ] Add GitLeaks orchestration to `scripts/security-check.sh`
- [ ] Update `scripts/generate-html-report.py` with GitLeaks imports
- [ ] Add GitLeaks visual summary support
- [ ] Test complete pipeline end-to-end
- [ ] Validate findings and report generation

## Deliverables
- File: `scripts/security-check.sh` - Updated with GitLeaks orchestration
- File: `scripts/generate-html-report.py` - Updated with GitLeaks integration
- File: `scripts/html_utils.py` - Updated with GitLeaks support (if needed)
- Tests: Complete scan with GitLeaks enabled
- Documentation: Updated README

## Implementation Steps

### Step 1: Update security-check.sh Orchestration
Add GitLeaks orchestration section after TruffleHog:

```bash
# Only run GitLeaks for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_gitleaks.sh
    log_message "--- Orchestrating GitLeaks Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export GITLEAKS_CONFIG_PATH="$GITLEAKS_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_gitleaks.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_gitleaks.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_gitleaks.sh"; then
            log_message "run_gitleaks.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_gitleaks.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_gitleaks.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- GitLeaks Scan Orchestration Finished ---"
else
    log_message "--- Skipping GitLeaks Scan (Website scan mode) ---"
fi
```

### Step 2: Update generate-html-report.py
Add GitLeaks import and processing:

```python
# Add import at top
from scripts.gitleaks_processor import gitleaks_summary, generate_gitleaks_html_section

# Add path variable
gitleaks_json_path = os.path.join(RESULTS_DIR, 'gitleaks.json')

# Add JSON reading
gitleaks_json = read_json(gitleaks_json_path)

# Add findings processing
gitleaks_findings = gitleaks_summary(gitleaks_json)

# Update visual summary call to include gitleaks_findings
f.write(generate_visual_summary_section(..., gitleaks_findings))

# Update overall summary call to include gitleaks_findings
f.write(generate_overall_summary_and_links_section(..., gitleaks_findings, ...))

# Add GitLeaks HTML section before footer
f.write(generate_gitleaks_html_section(gitleaks_findings))
```

### Step 3: Update html_utils.py
Update `generate_visual_summary_section` function to include GitLeaks:

```python
def generate_visual_summary_section(..., gitleaks_findings):
    # Add GitLeaks visual summary
    # Count findings and determine status
    # Add icon and link to findings
    ...
```

Update `generate_overall_summary_and_links_section` function:

```python
def generate_overall_summary_and_links_section(..., gitleaks_findings, ...):
    # Add GitLeaks summary line
    # Add GitLeaks link to report
    ...
```

### Step 4: Update false positive whitelist
Add GitLeaks-specific false positive patterns to `conf/fp_whitelist.json`:

```json
{
  "gitleaks": [
    {
      "pattern": "example-api-key",
      "reason": "Example test key"
    }
  ]
}
```

### Step 5: Build and Test
```bash
# Build Docker container
docker build -t simpleseccheck:latest .

# Test with sample repository
docker run --rm -v /path/to/repo:/target simpleseccheck:latest code

# Verify results
ls -la results/*/gitleaks.*
```

### Step 6: Update Documentation
Add GitLeaks to README.md:

```markdown
## GitLeaks Integration
GitLeaks scans repositories for hardcoded secrets and credentials using custom rules.

**Configuration**: `gitleaks/config.yaml`
**Output**: `results/[project]_[timestamp]/gitleaks.json`
```

## Dependencies
- Requires: Phase 2 completion (scripts and processor created)
- Blocks: None

## Estimated Time
2 hours

## Success Criteria
- [ ] GitLeaks runs successfully in security-check.sh orchestration
- [ ] HTML report includes GitLeaks findings section
- [ ] Visual summary shows GitLeaks status
- [ ] Links to GitLeaks reports work correctly
- [ ] Complete pipeline completes without errors
- [ ] LLM explanations are generated and displayed
- [ ] No false positives in clean repositories
- [ ] Docker container builds successfully

## Testing Checklist
- [ ] Run Docker build
- [ ] Execute scan on sample repository with secrets
- [ ] Verify GitLeaks JSON output exists
- [ ] Check HTML report includes GitLeaks section
- [ ] Verify visual summary shows GitLeaks status
- [ ] Test with repository without secrets (should show all clear)
- [ ] Test with repository with various secret types
- [ ] Verify LLM explanations are generated
- [ ] Check log files for errors
- [ ] Validate performance (< 5 minutes for standard repo)

## Validation Steps
1. Build Docker image with GitLeaks
2. Run security scan on test repository
3. Verify all output files are generated
4. Open HTML report and verify GitLeaks section
5. Check for any errors in logs
6. Test with different repository sizes
7. Verify findings are accurately reported

## Rollback Plan
If integration fails:
1. Remove GitLeaks orchestration from security-check.sh
2. Remove GitLeaks imports from generate-html-report.py
3. Revert html_utils.py changes
4. Rebuild Docker container

