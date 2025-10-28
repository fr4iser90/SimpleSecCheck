# Phase 3: Integration & Documentation

## Overview
- **Phase**: 3/3
- **Status**: completed
- **Estimated Time**: 3 hours
- **Progress**: 100%
- **Completed**: 2025-10-28T16:20:07.000Z

## Objectives
- Add scanners to main orchestrator
- Update HTML report generation
- Update documentation
- Test end-to-end

## Tasks

### Task 3.1: Integrate into Orchestrator (1h)
- [ ] Update `scripts/security-check.sh`:
  - [ ] Add project detection step
  - [ ] Call `project_detector.py`
  - [ ] Run Android scanner if detected
  - [ ] Run iOS scanner if detected
  - [ ] Add status tracking
- [ ] Update scanner status array
- [ ] Add error handling
- [ ] Test integration

### Task 3.2: Update HTML Reports (0.5h)
- [ ] Update `scripts/generate-html-report.py`
- [ ] Import Android processor
- [ ] Import iOS processor
- [ ] Add mobile findings section
- [ ] Add visual indicators

### Task 3.3: Add Report Section (0.5h)
- [ ] Create mobile section in HTML
- [ ] Show detected project type
- [ ] List Android findings
- [ ] List iOS findings
- [ ] Add severity breakdown

### Task 3.4: Update Documentation (0.5h)
- [ ] Update `README.md`
- [ ] Add mobile scanning section
- [ ] List supported checks
- [ ] Add usage examples

### Task 3.5: End-to-End Testing (0.5h)
- [ ] Test full workflow with native app
- [ ] Test project detection
- [ ] Test Android scanner
- [ ] Test iOS scanner
- [ ] Test report generation
- [ ] Verify findings appear

## Integration Points

### Main Orchestrator:
```bash
# In scripts/security-check.sh after Semgrep section
if [ "$SCAN_TYPE" = "code" ]; then
    IS_NATIVE=$(python3 /SimpleSecCheck/scripts/project_detector.py --target "$TARGET_PATH" --format json | jq -r '.has_native')
    
    if [ "$IS_NATIVE" = "true" ]; then
        # Run Android scanner
        /bin/bash "$TOOL_SCRIPTS_DIR/run_android_manifest_scanner.sh"
        
        # Run iOS scanner
        /bin/bash "$TOOL_SCRIPTS_DIR/run_ios_plist_scanner.sh"
    fi
fi
```

### HTML Report:
```python
# In scripts/generate-html-report.py
if mobile_findings:
    html_parts.append(generate_mobile_section(android_findings, ios_findings))
```

## Test Cases
- [ ] Full scan with Android/iOS app
- [ ] Full scan with Android-only app
- [ ] Full scan with iOS-only app
- [ ] Full scan with non-native project (skip)
- [ ] Report generation with findings
- [ ] Report generation with no findings

## Success Criteria
- [ ] Scanners integrated
- [ ] HTML reports updated
- [ ] Documentation updated
- [ ] End-to-end tests pass
- [ ] No regressions

## Dependencies
- Phase 1 completed
- Phase 2 completed

## Notes
- Follow existing patterns
- Keep integration simple
- Test thoroughly
- Document changes

