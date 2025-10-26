# Brakeman Integration – Phase 3: Integration & Testing

## Overview
This phase integrates Brakeman into the main security check system and performs testing.

## Status: Planning

## Objectives
- [ ] Update security-check.sh to include Brakeman
- [ ] Update generate-html-report.py to include Brakeman
- [ ] Add Brakeman to Dockerfile environment variables
- [ ] Test Brakeman with sample Ruby/Rails projects
- [ ] Validate error handling and edge cases

## Deliverables
- Updated: `scripts/security-check.sh` - Integration with main orchestrator
- Updated: `scripts/generate-html-report.py` - HTML report integration
- Updated: `Dockerfile` - Environment variable setup
- Updated: `conf/fp_whitelist.json` - False positive handling
- Test Results: Documented test scenarios and results

## Dependencies
- Requires: Phase 2 (Core Implementation)
- Blocks: None (final phase)

## Estimated Time
2 hours

## Success Criteria
- [ ] Brakeman is integrated into security-check.sh
- [ ] HTML reports include Brakeman findings
- [ ] Environment variables are properly set
- [ ] Tests pass with sample Ruby/Rails projects
- [ ] Error handling works correctly
- [ ] False positive whitelist is functional

## Implementation Details

### Step 1: Update security-check.sh
Add Brakeman orchestration to the main security check script:

```bash
# Add to tool-specific configurations section
export BRAKEMAN_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/brakeman/config.yaml"

# Add to tool execution section
if [ "$ENABLE_BRAKEMAN" = "true" ]; then
  log_message "[Security-Check] Starting Brakeman scan..."
  "$ORCHESTRATOR_SCRIPT_DIR/tools/run_brakeman.sh"
  log_message "[Security-Check] Brakeman scan completed."
fi
```

### Step 2: Update generate-html-report.py
Add Brakeman processor imports and HTML generation:

```python
# Add import at the top
from scripts.brakeman_processor import brakeman_summary, generate_brakeman_html_section

# Add to results processing section
try:
    brakeman_json = json.load(open(os.path.join(results_dir, 'brakeman.json'))) if os.path.exists(os.path.join(results_dir, 'brakeman.json')) else None
    brakeman_findings = brakeman_summary(brakeman_json)
    html_report_body_parts.append(generate_brakeman_html_section(brakeman_findings))
except Exception as e:
    debug(f"Error processing Brakeman results: {e}")
```

### Step 3: Update Dockerfile
Add Brakeman environment variables:

```dockerfile
# Set Brakeman environment variables
ENV BRAKEMAN_CONFIG_PATH=/SimpleSecCheck/brakeman/config.yaml
```

### Step 4: Update conf/fp_whitelist.json
Add Brakeman false positive whitelist section:

```json
{
  "brakeman": {
    "false_positives": [],
    "ignored_warnings": [],
    "excluded_files": []
  }
}
```

### Step 5: Testing
Test with various scenarios:

1. **Standard Ruby/Rails Application**
   - Run Brakeman on a standard Rails app
   - Verify findings are reported
   - Check JSON and text output

2. **Edge Cases**
   - Application with no security issues
   - Application with many security issues
   - Non-Rails Ruby application
   - Application with no Ruby files

3. **Error Handling**
   - Invalid target path
   - Missing configuration
   - Brakeman tool failure
   - Report generation failure

4. **Integration Testing**
   - Run full security check with Brakeman
   - Verify HTML report includes Brakeman section
   - Check LLM explanations are generated
   - Validate false positive whitelist

## Notes
- Test with real Ruby on Rails applications when possible
- Verify all Brakeman warning types are handled
- Check performance with large applications
- Ensure graceful handling of non-Rails projects

