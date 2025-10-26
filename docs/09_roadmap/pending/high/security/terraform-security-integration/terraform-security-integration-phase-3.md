# Terraform Security Integration – Phase 3: Integration & Testing

## Overview
Integrate Checkov with SimpleSecCheck main orchestrator, update HTML report generation, and test the integration.

## Objectives
- [ ] Integrate Checkov with main orchestrator
- [ ] Update HTML report generator
- [ ] Add Checkov to visual summary
- [ ] Add Checkov to false positive whitelist
- [ ] Test with sample Terraform projects

## Deliverables
- Modified: `scripts/security-check.sh` - Add Checkov orchestration
- Modified: `scripts/generate-html-report.py` - Add Checkov processing
- Modified: `scripts/html_utils.py` - Add Checkov to summaries
- Modified: `conf/fp_whitelist.json` - Add Checkov support
- Feature: Full system integration
- Feature: HTML report includes Checkov results

## Dependencies
- Requires: Phase 2 - Core Implementation completion
- Blocks: None

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov integrated with main orchestrator
- [ ] HTML report includes Checkov results
- [ ] Visual summary includes Checkov status
- [ ] Overall summary includes Checkov findings
- [ ] Links section includes Checkov reports
- [ ] False positive whitelist supports Checkov
- [ ] Integration tested with sample projects]

## Technical Details

### Main Orchestrator Integration
Location: `scripts/security-check.sh`

Add after existing tool integrations (around line 286, after SonarQube section):

```bash
# Only run Terraform security scan for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_terraform_security.sh
    log_message "--- Orchestrating Terraform Security Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export TERRAFORM_SECURITY_CONFIG_PATH="$BASE_PROJECT_DIR/terraform-security/config.yaml"
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
else
    log_message "--- Skipping Terraform Security Scan (Website scan mode) ---"
fi
```

Add environment variable at top of file (around line 32):

```bash
export TERRAFORM_SECURITY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/terraform-security/config.yaml"
```

### HTML Report Generator Updates
Location: `scripts/generate-html-report.py`

Add import at top of file:
```python
from terraform_security_processor import checkov_summary, generate_checkov_html_section
```

Add processing logic (after other tool processors, around line 200):

```python
# Process Checkov results
checkov_json = None
checkov_json_path = os.path.join(RESULTS_DIR, 'checkov.json')
if os.path.exists(checkov_json_path):
    try:
        with open(checkov_json_path, 'r') as f:
            checkov_json = json.load(f)
    except Exception as e:
        debug(f"Error loading checkov.json: {e}")

checkov_findings = None
checkov_html = None
if checkov_json:
    checkov_findings = checkov_summary(checkov_json)
    if checkov_findings:
        checkov_html = generate_checkov_html_section(checkov_findings)
        tool_html_parts.append(checkov_html)
```

### HTML Utils Updates
Location: `scripts/html_utils.py`

Add Checkov to visual summary function (around line 150):

```python
def create_visual_summary(trivy_summary, semgrep_summary, codeql_summary, nuclei_summary, owasp_summary, safety_summary, snyk_summary, sonarqube_summary, checkov_summary):
    # ... existing code ...
    # Add Checkov status
    if checkov_summary and any(f.get('severity') == 'HIGH' for f in checkov_summary):
        visual_parts.append('🚨')  # High severity Checkov findings
    elif checkov_summary:
        visual_parts.append('⚠️')  # Medium/low Checkov findings
    else:
        visual_parts.append('✅')  # No Checkov findings
    
    # ... rest of function ...
```

### False Positive Whitelist Updates
Location: `conf/fp_whitelist.json`

Add Checkov section:

```json
{
  "checkov": {
    "enabled": true,
    "checks": []
  }
}
```

## Implementation Steps

### Step 1: Update Main Orchestrator
1. Open `scripts/security-check.sh`
2. Add environment variable export
3. Add Checkov execution section after SonarQube
4. Follow existing pattern for orchestration

### Step 2: Update HTML Report Generator
1. Open `scripts/generate-html-report.py`
2. Add import for Checkov processor
3. Add Checkov processing logic
4. Integrate with HTML generation

### Step 3: Update HTML Utils
1. Open `scripts/html_utils.py`
2. Update visual summary function
3. Add Checkov status icon

### Step 4: Update False Positive Whitelist
1. Open `conf/fp_whitelist.json`
2. Add Checkov section
3. Configure whitelist entries

### Step 5: Make Script Executable
1. Run: `chmod +x scripts/tools/run_terraform_security.sh`
2. Verify permissions

### Step 6: Test Integration
1. Build Docker image
2. Run security check with sample Terraform code
3. Verify Checkov reports generated
4. Verify HTML report includes Checkov
5. Test error handling

## Testing Scenarios

### Test 1: Terraform Project with Security Issues
1. Create sample Terraform project
2. Add intentionally insecure configurations
3. Run SimpleSecCheck
4. Verify Checkov finds issues
5. Verify HTML report shows issues

### Test 2: Terraform Project with No Issues
1. Create secure Terraform project
2. Run SimpleSecCheck
3. Verify Checkov reports no issues
4. Verify HTML report shows all clear

### Test 3: Non-Terraform Project
1. Run SimpleSecCheck on Python project
2. Verify Checkov skips gracefully
3. Verify no errors in logs

## Notes
- Follow existing integration patterns exactly
- Maintain consistency with other tool integrations
- Test all error scenarios
- Document any Checkov-specific behavior

