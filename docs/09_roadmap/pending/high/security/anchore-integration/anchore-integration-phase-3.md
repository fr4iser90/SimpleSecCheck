# Anchore Integration – Phase 3: Integration & Testing

## Overview
Integrate Anchore into the main security check orchestrator and HTML report generator, then test the end-to-end pipeline.

## Objectives
- [ ] Update main orchestrator script
- [ ] Update HTML report generator
- [ ] Add Anchore to false positive whitelist
- [ ] Test end-to-end pipeline
- [ ] Validate integration with Trivy and Clair

## Deliverables
- Updated file: `scripts/security-check.sh` - Anchore integration
- Updated file: `scripts/generate-html-report.py` - Anchore report section
- Updated file: `conf/fp_whitelist.json` - Anchore false positive handling
- Test results: End-to-end pipeline validation

## Implementation Steps

### 1. Update Main Orchestrator Script
**Location**: `scripts/security-check.sh`  
**Action**: Add Anchore orchestration section after Clair

Find the section for Clair (around line 470-490) and add:

```bash
    log_message "--- Orchestrating Anchore Container Image Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export ANCHORE_CONFIG_PATH="$ANCHORE_CONFIG_PATH_IN_CONTAINER"
    export ANCHORE_IMAGE="$ANCHORE_IMAGE"
    if [ -f "$TOOL_SCRIPTS_DIR/run_anchore.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_anchore.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_anchore.sh"; then
            log_message "run_anchore.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_anchore.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_anchore.sh not found!"
        OVERALL_SUCCESS=false
    fi
```

Also add the ANCHORE_CONFIG_PATH_IN_CONTAINER and ANCHORE_IMAGE variables at the top:

```bash
export ANCHORE_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/anchore/config.yaml"
export ANCHORE_IMAGE="${ANCHORE_IMAGE:-}"
```

### 2. Update HTML Report Generator
**Location**: `scripts/generate-html-report.py`  
**Action**: Add Anchore import and HTML section generation

Add import at the top (after clair imports):
```python
from scripts.anchore_processor import anchore_summary, generate_anchore_html_section
```

Add to path definitions (after clair_json_path):
```python
anchore_json_path = os.path.join(RESULTS_DIR, 'anchore.json')
```

Add to JSON reading (after clair_json):
```python
anchore_json = read_json(anchore_json_path)
```

Add to LLM processing (after clair_vulns):
```python
try:
    anchor_vulns = anchore_summary(anchore_json) if anchore_json else []
except Exception as e:
    debug(f"Error processing Anchore results: {e}")
    anchore_vulns = []
```

Add to HTML sections generation (after Clair section):
```python
    html_parts.append(generate_anchore_html_section(anchore_vulns))
```

### 3. Add Anchore Configuration to Docker Compose
**Location**: `docker-compose.yml`  
**Action**: Add Anchore volume mount and environment variable

Add to volumes section:
```yaml
- ./anchore:/SimpleSecCheck/anchore
```

Add to environment variables:
```yaml
- ANCHORE_CONFIG_PATH_IN_CONTAINER=/SimpleSecCheck/anchore/config.yaml
- ANCHORE_IMAGE=${ANCHORE_IMAGE:-}
```

### 4. Update False Positive Whitelist
**Location**: `conf/fp_whitelist.json`  
**Action**: Add Anchore section for future false positive handling

```json
{
  "anchore": {
    "vulnerabilities": [],
    "packages": [],
    "cvss_threshold": 7.0
  }
}
```

## Dependencies
- Requires: Phase 2 (Core Implementation)
- Blocks: Task completion

## Estimated Time
2 hours

## Success Criteria
- [ ] Orchestrator calls Anchore script
- [ ] HTML report includes Anchore section
- [ ] Configuration is loaded correctly
- [ ] End-to-end pipeline completes successfully
- [ ] No conflicts with Trivy or Clair
- [ ] Reports show Anchore findings

## Testing

### 1. Unit Tests
- [ ] Test orchestrator integration: Run `scripts/security-check.sh` manually
- [ ] Test HTML generation: Verify Anchore section appears in report
- [ ] Test configuration loading: Verify config file is read correctly

### 2. Integration Tests
- [ ] Test with sample Docker image: `ANCHORE_IMAGE=alpine:latest`
- [ ] Test with vulnerable image to verify findings
- [ ] Test with clean image (should show no vulnerabilities)
- [ ] Test error handling (invalid image, missing grype)

### 3. End-to-End Tests
- [ ] Full pipeline with Anchore: `./run-docker.sh /path/to/project`
- [ ] Verify all three tools run (Trivy, Clair, Anchore)
- [ ] Verify report includes all three sections
- [ ] Verify no conflicts between tools
- [ ] Verify false positive whitelist is applied

### 4. Validation Tests
- [ ] Compare Anchore findings with Trivy findings
- [ ] Verify consistency in vulnerability detection
- [ ] Check report formatting and layout
- [ ] Validate performance (should not significantly increase scan time)

## Testing Scenarios

### Scenario 1: Clean Image
```bash
ANCHORE_IMAGE=alpine:latest ./run-docker.sh
```
Expected: Report shows no vulnerabilities (or existing known issues)

### Scenario 2: Vulnerable Image
```bash
ANCHORE_IMAGE=python:3.7 ./run-docker.sh
```
Expected: Report shows multiple vulnerabilities

### Scenario 3: Integration with Other Tools
```bash
SCAN_TYPE=code ./run-docker.sh /path/to/code
```
Expected: All three tools (Trivy, Clair, Anchore) run and show results

## Notes
- Anchore should work alongside Trivy and Clair without conflicts
- Each tool may detect slightly different vulnerabilities
- Report should clearly separate findings from each tool
- Performance impact should be minimal (all tools can run in parallel)
- Configuration should allow enabling/disabling individual tools

## Rollback Instructions
If issues are encountered:
1. Comment out Anchore section in `scripts/security-check.sh`
2. Remove Anchore import from `scripts/generate-html-report.py`
3. Anchore CLI remains installed but unused

## Post-Implementation
- [ ] Update README.md with Anchore integration details
- [ ] Add Anchore to documentation
- [ ] Update configuration examples
- [ ] Add troubleshooting section if needed

