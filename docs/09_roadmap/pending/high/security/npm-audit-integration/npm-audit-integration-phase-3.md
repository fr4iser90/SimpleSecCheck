# npm audit Integration – Phase 3: Integration & Testing

## Overview
Integrate npm audit into the main security-check orchestrator, HTML report generator, and visual summary system.

## Objectives
- [ ] Integrate npm audit into security-check.sh
- [ ] Add npm audit to HTML report generator
- [ ] Update visual summary section
- [ ] Add npm audit to false positive whitelist
- [ ] Test complete integration
- [ ] Validate with sample projects

## Deliverables
- File: `scripts/security-check.sh` - Updated with npm audit orchestration
- File: `scripts/generate-html-report.py` - Updated with npm audit processing
- File: `scripts/html_utils.py` - Updated with npm audit visual summary
- File: `conf/fp_whitelist.json` - Updated with npm audit false positives
- Tests: Integration tests with sample Node.js projects

## Dependencies
- Requires: Phase 2 - Core Implementation completion
- Blocks: None

## Estimated Time
2 hours

## Success Criteria
- [ ] npm audit integrated into security-check.sh
- [ ] npm audit findings appear in HTML reports
- [ ] npm audit included in visual summary
- [ ] False positive whitelist supports npm audit
- [ ] All integration tests passing
- [ ] Sample projects tested successfully

## Technical Details

### security-check.sh Integration
Add npm audit orchestration section after other code scanning tools:

```bash
# Only run npm audit for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_npm_audit.sh
    log_message "--- Orchestrating npm audit Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export LOG_FILE="$LOGS_DIR_IN_CONTAINER/security-check.log"
    export NPM_AUDIT_CONFIG_PATH="$BASE_PROJECT_DIR/npm-audit/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_npm_audit.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_npm_audit.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_npm_audit.sh"; then
            log_message "run_npm_audit.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_npm_audit.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_npm_audit.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- npm audit Scan Orchestration Finished ---"
else
    log_message "--- Skipping npm audit Scan (Website scan mode) ---"
fi
```

### generate-html-report.py Integration
Add npm audit import and processing:

```python
from scripts.npm_audit_processor import npm_audit_summary, generate_npm_audit_html_section

# In main() function:
npm_audit_json_path = os.path.join(RESULTS_DIR, 'npm-audit.json')
npm_audit_json = read_json(npm_audit_json_path)
npm_audit_findings = npm_audit_summary(npm_audit_json)

# In HTML generation:
f.write(generate_npm_audit_html_section(npm_audit_findings))
```

### html_utils.py Integration
Update generate_visual_summary_section to include npm_audit_findings parameter and visual element.

Add npm audit visual summary section:

```python
def generate_visual_summary_section(..., npm_audit_findings):
    # Add npm audit visual element
    npm_audit_count = len(npm_audit_findings) if npm_audit_findings else 0
    npm_audit_sev = determine_severity(npm_audit_findings)
    html_parts.append(f'<div class="tool-summary npm-audit">{npm_audit_sev} npm audit</div>')
```

### False Positive Whitelist
Update conf/fp_whitelist.json:

```json
{
  "npm_audit": {
    "ignored_packages": [],
    "ignored_advisories": [],
    "ignored_severities": []
  }
}
```

### Environment Variables
Add to security-check.sh:

```bash
export NPM_AUDIT_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/npm-audit/config.yaml"
```

### Testing Strategy

#### Unit Tests
- [ ] Test npm_audit_summary() with sample JSON
- [ ] Test generate_npm_audit_html_section() with various findings
- [ ] Test error handling and edge cases

#### Integration Tests
- [ ] Test with sample Node.js project
- [ ] Test integration with security-check.sh
- [ ] Test HTML report generation with npm audit findings
- [ ] Test LLM explanation integration

#### E2E Tests
- [ ] Test complete scan workflow
- [ ] Verify findings appear correctly in HTML report
- [ ] Test multiple package.json files
- [ ] Test with projects having no vulnerabilities
- [ ] Test with projects having various vulnerability levels

### Sample Test Projects
1. Simple project with package.json (no vulnerabilities)
2. Project with known vulnerable dependencies
3. Multi-package project (monorepo style)
4. Project with package-lock.json
5. Project without lock files

### Validation Checklist
- [ ] npm audit runs successfully in container
- [ ] Findings correctly parsed and displayed
- [ ] Visual summary shows correct status
- [ ] LLM explanations work
- [ ] No impact on other scanning tools
- [ ] Performance acceptable (< 1 minute for typical projects)
- [ ] Error handling works gracefully
- [ ] Documentation complete

### Rollback Plan
- [ ] Remove npm audit from security-check.sh orchestration
- [ ] Remove npm audit imports from generate-html-report.py
- [ ] Remove npm audit from html_utils.py
- [ ] Keep npm audit script and processor for future use

### Notes
- npm audit is lightweight and fast compared to other tools
- Works best when package-lock.json is present
- May need npm install in some cases
- Does not require internet connection (uses npm cache)
- Works with both npm and yarn projects

