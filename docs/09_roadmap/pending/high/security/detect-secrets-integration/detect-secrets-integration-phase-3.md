# Detect-secrets Integration – Phase 3: Integration & Testing

## Overview
Integrate detect-secrets into the main SimpleSecCheck orchestrator, update the HTML report generator, add false positive handling, and perform testing with real code projects to validate the integration.

## Objectives
- [ ] Update `scripts/security-check.sh` to include detect-secrets
- [ ] Update HTML report generator with detect-secrets import
- [ ] Add detect-secrets to false positive whitelist
- [ ] Test with sample code projects
- [ ] Validate detect-secrets findings
- [ ] Update documentation

## Deliverables
- Modified File: `scripts/security-check.sh` - Added detect-secrets orchestration
- Modified File: `scripts/generate-html-report.py` - Added detect-secrets import and section generation
- Modified File: `conf/fp_whitelist.json` - Added detect-secrets false positive handling
- Test Results: Verified working integration
- Documentation: Updated README if needed

## Dependencies
- Requires: Phase 1 and Phase 2 completion
- Blocks: None (this is the final phase)

## Estimated Time
2 hours

## Success Criteria
- [ ] Detect-secrets appears in security-check.sh orchestrator
- [ ] Detect-secrets results are included in HTML reports
- [ ] False positive handling works correctly
- [ ] Full integration test passes
- [ ] Documentation is updated
- [ ] No regressions in existing functionality

## Implementation Details

### 1. Update Main Orchestrator
File: `scripts/security-check.sh`

Add detect-secrets environment variable (around line 34, after GitLeaks):
```bash
export DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/detect-secrets/config.yaml"
```

Log environment variable (around line 94, after GitLeaks):
```bash
log_message "Detect-secrets Config Path (DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER): $DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER"
```

Add detect-secrets execution (in code scan section, around line 200-250, after GitLeaks):
```bash
# --- Detect-secrets Execution ---
log_message "Running detect-secrets..."
if [ -d "$TARGET_PATH_IN_CONTAINER" ]; then
    bash "$TOOL_SCRIPTS_DIR/run_detect_secrets.sh"
    log_message "Detect-secrets completed."
else
    log_message "[Detect-secrets] Skipping (no code directory found)."
fi
```

### 2. Update HTML Report Generator
File: `scripts/generate-html-report.py`

Add import (around line 10, with other processor imports):
```python
from scripts.detect_secrets_processor import detect_secrets_summary, generate_detect_secrets_html_section
```

Add variable for detect-secrets results (around line 30, with other tool results):
```python
detect_secrets_findings = []
```

Load detect-secrets results (around line 60, with other tool result loading):
```python
# Load detect-secrets results
try:
    with open(f"{args.output_dir}/detect-secrets.json", 'r') as f:
        detect_secrets_data = json.load(f)
        detect_secrets_findings = detect_secrets_summary(detect_secrets_data)
except FileNotFoundError:
    pass
except json.JSONDecodeError:
    pass
```

Generate HTML section (around line 80, with other HTML sections):
```python
html_parts.append(generate_detect_secrets_html_section(detect_secrets_findings))
```

### 3. Update False Positive Whitelist
File: `conf/fp_whitelist.json`

Add detect-secrets section (following existing pattern):
```json
{
  "detect_secrets": {
    "excluded_files": [],
    "excluded_patterns": [],
    "known_false_positives": []
  }
}
```

### 4. Testing Checklist

#### Unit Tests:
- [ ] Test detect-secrets execution script with sample project
- [ ] Test processor with sample JSON output
- [ ] Test HTML section generation
- [ ] Test error handling

#### Integration Tests:
- [ ] Test detect-secrets in code scan mode
- [ ] Verify detect-secrets appears in security-check.sh logs
- [ ] Verify detect-secrets results appear in HTML report
- [ ] Test false positive handling
- [ ] Test error scenarios (missing detect-secrets, invalid config)

#### End-to-End Tests:
- [ ] Run full SimpleSecCheck scan with detect-secrets enabled
- [ ] Verify complete pipeline works: scan -> process -> HTML report
- [ ] Verify no regressions in existing tools
- [ ] Test with various code projects

### 5. Documentation Updates

#### README.md
Add detect-secrets to list of supported tools (if applicable)

#### CHANGELOG.md
Add entry for detect-secrets integration:
```
## [Unreleased]
### Added
- Detect-secrets integration for secret detection
- Detect-secrets configuration support
- Detect-secrets HTML report generation
```

### 6. Validation Commands

After implementation, run:
```bash
# Test Docker build
docker build -t simpleseccheck .

# Test detect-secrets is installed
docker run --rm simpleseccheck detect-secrets --version

# Test full scan
docker run --rm -v /path/to/project:/target simpleseccheck bash scripts/security-check.sh

# Check logs
cat results/[timestamp]/logs/security-check.log | grep detect-secrets

# Check HTML report
open results/[timestamp]/security-summary.html
```

## Notes
- Follow existing integration patterns from GitLeaks and TruffleHog
- Ensure error handling doesn't break the entire scan
- Log all detect-secrets activities for debugging
- Maintain consistency with other tool integrations

## Rollback Steps
If issues occur:
1. Comment out detect-secrets execution in security-check.sh
2. Remove detect-secrets processor import from generate-html-report.py
3. Restore previous versions of modified files
4. Document issues for future fixes

## Post-Implementation
- Monitor for any issues in production usage
- Collect feedback on detect-secrets findings
- Adjust configuration based on false positive rates
- Consider performance optimizations if needed

