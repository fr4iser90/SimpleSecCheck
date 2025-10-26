# Nikto Integration – Phase 3: Integration & Testing

## Overview
Integrate Nikto into the main SimpleSecCheck orchestration system, update Dockerfile, update HTML report generation, and test the complete integration.

## Objectives
- [ ] Update scripts/security-check.sh to include Nikto orchestration
- [ ] Update Dockerfile with Nikto installation
- [ ] Update generate-html-report.py to include Nikto section
- [ ] Test complete Nikto integration

## Deliverables
- [ ] Nikto orchestration added to security-check.sh
- [ ] Nikto installation added to Dockerfile
- [ ] Nikto HTML section added to report generator
- [ ] Complete integration tested and working

## Dependencies
- Requires: Phase 2 completion (Nikto processor created)
- Blocks: None (final integration phase)

## Estimated Time
2 hours

## Success Criteria
- [ ] Nikto runs in website scan mode
- [ ] Nikto results appear in HTML report
- [ ] Integration works with security-check.sh
- [ ] Error handling works correctly
- [ ] All tests pass without errors

## Technical Details

### 3.1 Security Check Integration
Add Nikto orchestration to `scripts/security-check.sh`:
```bash
# Only run Nikto for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_nikto.sh
    log_message "--- Orchestrating Nikto Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export NIKTO_CONFIG_PATH="$BASE_PROJECT_DIR/nikto/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_nikto.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_nikto.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_nikto.sh"; then
            log_message "run_nikto.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_nikto.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_nikto.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Nikto Scan Orchestration Finished ---"
else
    log_message "--- Skipping Nikto Scan (Code scan mode) ---"
fi
```

### 3.2 Dockerfile Updates
Ensure Nikto is installed (already added in Phase 1):
```dockerfile
# Install Nikto
RUN apt-get update && apt-get install -y perl libwww-perl liblwp-protocol-https-perl \
    && wget https://github.com/sullo/nikto/archive/master.zip \
    && unzip master.zip \
    && mv nikto-master /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && rm master.zip
```

Add environment variable:
```dockerfile
# Set Nikto environment variables
ENV NIKTO_CONFIG_PATH=/SimpleSecCheck/nikto/config.yaml
```

### 3.3 HTML Report Updates
Add to `scripts/generate-html-report.py`:
```python
from scripts.nikto_processor import nikto_summary, generate_nikto_html_section

# In the main function, add:
# Process Nikto results
NIKTO_JSON = os.path.join(RESULTS_DIR, "nikto.json")
if os.path.exists(NIKTO_JSON):
    with open(NIKTO_JSON, 'r') as f:
        nikto_json = json.load(f)
    nikto_findings = nikto_summary(nikto_json)
    nikto_html = generate_nikto_html_section(nikto_findings)
    html_parts.append(nikto_html)
```

### 3.4 Testing & Validation
Test complete integration:
```bash
# Test with sample website
./run-docker.sh https://example.com

# Verify results
ls -la results/
cat results/nikto.json
cat results/security-summary.html
```

## Notes
- Nikto should only run in website scan mode, similar to ZAP and Nuclei
- Error handling should follow existing patterns
- HTML report should include Nikto section with findings
- Follow existing processor integration patterns from Wapiti and ZAP

## Implementation Steps
1. Add Nikto orchestration section to security-check.sh
2. Verify Nikto installation in Dockerfile
3. Add environment variables to Dockerfile
4. Update generate-html-report.py with Nikto processor
5. Test with sample website
6. Verify HTML report generation
7. Test error handling
8. Document integration

