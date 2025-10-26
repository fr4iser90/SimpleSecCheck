# Kube-hunter Integration – Phase 3: Integration & Testing

## Overview
This phase integrates Kube-hunter into the main security-check system, updates HTML report generation, and conducts testing and validation.

## Objectives
- [ ] Integrate Kube-hunter into security-check.sh orchestrator
- [ ] Update HTML report generator with Kube-hunter section
- [ ] Update HTML utilities for visual summary
- [ ] Conduct system testing and validation
- [ ] Document integration and usage

## Deliverables
- File: `scripts/security-check.sh` - Updated with Kube-hunter orchestration
- File: `scripts/generate-html-report.py` - Updated with Kube-hunter HTML generation
- File: `scripts/html_utils.py` - Updated with Kube-hunter visual summary
- Test: End-to-end integration test
- Documentation: Usage instructions

## Dependencies
- Requires: Phase 2 completion (Script and processor created)
- Blocks: Task completion

## Implementation Steps

### Step 1: Update security-check.sh (45 minutes)
- Add Kube-hunter orchestration block
- Set up environment variables
- Add conditional execution logic
- Handle website vs code scan modes
- Add error handling and logging

### Step 2: Update HTML Report Generation (30 minutes)
- Import kube_hunter_processor in generate-html-report.py
- Add Kube-hunter JSON file path
- Call kube_hunter_summary and generate HTML section
- Add to visual summary section
- Update overall summary

### Step 3: Update HTML Utilities (30 minutes)
- Add Kube-hunter to generate_visual_summary_section()
- Add icon and severity handling
- Update generate_overall_summary_and_links_section()
- Add Kube-hunter to report links

### Step 4: Testing & Validation (15 minutes)
- Test complete integration workflow
- Verify HTML report generation
- Test with sample Kubernetes cluster
- Verify error handling and logging
- Check visual summary display

## Estimated Time
2 hours

## Success Criteria
- [ ] Kube-hunter integration visible in security-check.sh
- [ ] HTML report includes Kube-hunter section
- [ ] Visual summary shows Kube-hunter results
- [ ] All links to raw reports work
- [ ] Integration tested successfully
- [ ] Documentation complete

## Notes
- Follow existing integration patterns from other tools
- Ensure proper error handling when cluster is unavailable
- Support both active and passive scan modes
- Handle authentication and authorization properly
- Document any cluster access requirements

