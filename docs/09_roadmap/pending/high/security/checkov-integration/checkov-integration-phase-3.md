# Checkov Integration – Phase 3: Integration & Testing

## Overview
Integrate Checkov into the main security-check orchestrator, update HTML report generation, add false positive support, and test the complete integration with sample projects.

## Objectives
- [ ] Update scripts/security-check.sh to include Checkov
- [ ] Update scripts/generate-html-report.py to process Checkov results
- [ ] Update scripts/html_utils.py to include Checkov in summaries
- [ ] Add Checkov support to conf/fp_whitelist.json
- [ ] Test with sample infrastructure projects
- [ ] Verify complete workflow

## Deliverables
- Integration: Checkov in main orchestrator
- Integration: Checkov in HTML report generator
- Integration: Checkov in false positive whitelist
- Test: Sample infrastructure project scan

## Dependencies
- Requires: Phase 2 completion (Core Implementation)
- Blocks: Task completion

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov integrated into main orchestrator
- [ ] HTML reports include Checkov results
- [ ] Visual summary shows Checkov status
- [ ] Overall summary includes Checkov findings
- [ ] False positive whitelist works
- [ ] All tests pass

## Implementation Steps

### Step 1: Update Main Orchestrator
Add Checkov to `scripts/security-check.sh`:

```bash
# Add Checkov environment variables at the top
export CHECKOV_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/checkov/config.yaml"

# Add Checkov execution section (after terraform_security section)
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "--- Orchestrating Checkov Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export CHECKOV_CONFIG_PATH="$CHECKOV_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_checkov.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_checkov.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_checkov.sh"; then
            log_message "run_checkov.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_checkov.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_checkov.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Checkov Scan Orchestration Finished ---"
else
    log_message "--- Skipping Checkov Scan (Website scan mode) ---"
fi
```

### Step 2: Update HTML Report Generator
Update `scripts/generate-html-report.py`:

```python
# Add Checkov processor import at the top
from scripts.checkov_processor import checkov_summary, generate_checkov_html_section

# In the report generation function, add Checkov processing
def generate_html_report(results_dir):
    # ... existing code ...
    
    # Process Checkov results
    checkov_json_path = os.path.join(results_dir, 'checkov.json')
    if os.path.exists(checkov_json_path):
        with open(checkov_json_path, 'r') as f:
            checkov_data = json.load(f)
        checkov_findings = checkov_summary(checkov_data)
        checkov_html = generate_checkov_html_section(checkov_findings)
        html_parts.append(checkov_html)
    
    # ... rest of function ...
```

### Step 3: Update Visual Summary
Update `scripts/html_utils.py` to include Checkov in the visual summary:

```python
def generate_visual_summary_section(all_tool_results):
    # ... existing code ...
    
    # Add Checkov status
    checkov_status = check_tool_status(all_tool_results, 'checkov')
    summary_list.append({
        'tool': 'Checkov',
        'status': checkov_status,
        'count': checkov_status.get('issue_count', 0)
    })
    
    # ... rest of function ...
```

### Step 4: Update False Positive Whitelist
Add Checkov support to `conf/fp_whitelist.json`:

```json
{
  "tools": {
    "checkov": {
      "enabled": true,
      "patterns": [
        {
          "check_id": "CKV_AWS_*",
          "description": "AWS-specific checks",
          "reason": "Not applicable for this environment"
        }
      ]
    }
  }
}
```

### Step 5: Test with Sample Project
Create a test with sample infrastructure files:

```bash
# Create sample Terraform file
mkdir -p /tmp/test-terraform
cat > /tmp/test-terraform/main.tf << 'EOF'
resource "aws_s3_bucket" "test" {
  bucket = "test-bucket"
  acl    = "public-read"
}
EOF

# Run scan
./run-docker.sh /tmp/test-terraform
```

## Testing Checklist
- [ ] Checkov scan executes without errors
- [ ] JSON and text reports generated
- [ ] HTML report includes Checkov section
- [ ] LLM explanations appear in HTML
- [ ] Visual summary shows Checkov status
- [ ] Overall summary counts Checkov findings
- [ ] Links section includes Checkov reports
- [ ] False positive whitelist works
- [ ] Error handling works for missing Checkov
- [ ] Logs show proper Checkov execution

## Notes
- Verify this doesn't duplicate terraform_security integration
- Consider if consolidation is needed if both handle Checkov
- Ensure proper error handling throughout

