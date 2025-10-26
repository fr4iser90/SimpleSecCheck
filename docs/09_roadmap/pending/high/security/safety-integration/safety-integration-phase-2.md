# Safety Integration – Phase 2: Core Implementation

## Overview
Create Safety script and processor for Python dependency vulnerability scanning and report generation.

## Objectives
- [ ] Create Safety execution script
- [ ] Create Safety processor for result parsing
- [ ] Implement JSON and text report generation
- [ ] Add support for requirements.txt and Pipfile scanning
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_safety.sh` - Safety execution script
- File: `scripts/safety_processor.py` - Safety result processor
- Feature: JSON and text report generation
- Feature: Requirements.txt and Pipfile scanning support
- Feature: LLM integration for explanations

## Dependencies
- Requires: Phase 1 - Foundation Setup completion
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] Safety script generates JSON and text reports
- [ ] Safety processor parses results correctly
- [ ] Safety processor generates HTML sections
- [ ] Safety processor integrates with LLM explanations
- [ ] Safety script handles requirements.txt and Pipfile
- [ ] Error handling works for failed scans

## Technical Details

### Safety Script Implementation
```bash
#!/bin/bash
# Individual Safety Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SAFETY_CONFIG_PATH="${SAFETY_CONFIG_PATH:-/SimpleSecCheck/safety/config.yaml}"

# Generate JSON report
safety check --json --output "$RESULTS_DIR/safety.json" --file "$TARGET_PATH/requirements.txt"

# Generate text report
safety check --output "$RESULTS_DIR/safety.txt" --file "$TARGET_PATH/requirements.txt"

# Additional Pipfile scan if present
if [ -f "$TARGET_PATH/Pipfile" ]; then
    safety check --json --output "$RESULTS_DIR/safety-pipfile.json" --file "$TARGET_PATH/Pipfile"
fi
```

### Safety Processor Implementation
```python
#!/usr/bin/env python3
import sys
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[safety_processor] {msg}", file=sys.stderr)

def safety_summary(safety_json):
    vulns = []
    if safety_json and isinstance(safety_json, list):
        for v in safety_json:
            vulns.append({
                'package': v.get('package', ''),
                'installed_version': v.get('installed_version', ''),
                'vulnerability_id': v.get('vulnerability_id', ''),
                'vulnerable_spec': v.get('vulnerable_spec', ''),
                'advisory': v.get('advisory', ''),
                'severity': v.get('severity', 'MEDIUM')
            })
    return vulns

def generate_safety_html_section(safety_vulns):
    html_parts = []
    html_parts.append('<h2>Safety Python Dependency Scan</h2>')
    if safety_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Version</th><th>Vulnerability</th><th>Severity</th><th>Advisory</th><th>AI Explanation</th></tr>')
        for v in safety_vulns:
            # Generate AI explanation
            prompt = f"Explain this Python dependency vulnerability: {v['package']} {v['installed_version']} - {v['advisory']}"
            try:
                if llm_client:
                    ai_explanation = llm_client.query(prompt)
                else:
                    ai_explanation = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for Safety finding: {e}")
                ai_explanation = "Error fetching AI explanation."
            
            # HTML generation with proper escaping
            # ... (implementation details)
        html_parts.append('</table>')
    else:
        html_parts.append('<p>No Python dependency vulnerabilities found.</p>')
    return '\n'.join(html_parts)
```

### Testing Requirements
- Test with sample requirements.txt files
- Test with Pipfile scanning
- Test JSON and text report generation
- Test error handling for missing files
- Test LLM integration for explanations
- Validate HTML generation
