# Detect-secrets Integration – Phase 2: Core Implementation

## Overview
Create the core components for detect-secrets integration: the execution script and the results processor. Implement secret detection scanning, result parsing, and HTML report generation with LLM explanation support.

## Objectives
- [ ] Create: `scripts/tools/run_detect_secrets.sh`
- [ ] Implement detect-secrets scanning script
- [ ] Support JSON output format
- [ ] Generate text reports
- [ ] Create: `scripts/detect_secrets_processor.py`
- [ ] Parse detect-secrets JSON results
- [ ] Generate HTML sections for reports
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_detect_secrets.sh` - Execution script for detect-secrets
- File: `scripts/detect_secrets_processor.py` - Results processor with LLM support

## Dependencies
- Requires: Phase 1 completion (detect-secrets installation and configuration)
- Blocks: Phase 3 (Integration & Testing)

## Estimated Time
2 hours

## Success Criteria
- [ ] `run_detect_secrets.sh` script is executable
- [ ] Script handles environment variables correctly
- [ ] Script generates JSON and text reports
- [ ] Script logs output to central log file
- [ ] `detect_secrets_processor.py` parses JSON correctly
- [ ] Processor generates HTML sections properly
- [ ] LLM explanations are generated for findings
- [ ] Processor handles errors gracefully

## Implementation Details

### 1. Create Execution Script
File: `scripts/tools/run_detect_secrets.sh`

Template based on `run_gitleaks.sh`:
```bash
#!/bin/bash
# Individual Detect-secrets Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# DETECT_SECRETS_CONFIG_PATH: Path to detect-secrets configuration file.

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
DETECT_SECRETS_CONFIG_PATH="${DETECT_SECRETS_CONFIG_PATH:-/SimpleSecCheck/detect-secrets/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_detect_secrets.sh] Initializing detect-secrets scan..." | tee -a "$LOG_FILE"

if command -v detect-secrets &>/dev/null; then
  echo "[run_detect_secrets.sh][Detect-secrets] Running secret detection scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  DETECT_SECRETS_JSON="$RESULTS_DIR/detect-secrets.json"
  DETECT_SECRETS_TEXT="$RESULTS_DIR/detect-secrets.txt"
  
  # Run secret detection scan with JSON output
  echo "[run_detect_secrets.sh][Detect-secrets] Running secret detection scan..." | tee -a "$LOG_FILE"
  detect-secrets scan --config "$DETECT_SECRETS_CONFIG_PATH" "$TARGET_PATH" > "$DETECT_SECRETS_JSON" 2>>"$LOG_FILE" || {
    echo "[run_detect_secrets.sh][Detect-secrets] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  echo "[run_detect_secrets.sh][Detect-secrets] Running text report generation..." | tee -a "$LOG_FILE"
  detect-secrets scan --config "$DETECT_SECRETS_CONFIG_PATH" "$TARGET_PATH" > "$DETECT_SECRETS_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_detect_secrets.sh][Detect-secrets] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$DETECT_SECRETS_JSON" ] || [ -f "$DETECT_SECRETS_TEXT" ]; then
    echo "[run_detect_secrets.sh][Detect-secrets] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$DETECT_SECRETS_JSON" ] && echo "  - $DETECT_SECRETS_JSON" | tee -a "$LOG_FILE"
    [ -f "$DETECT_SECRETS_TEXT" ] && echo "  - $DETECT_SECRETS_TEXT" | tee -a "$LOG_FILE"
    echo "[Detect-secrets] Secret detection scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_detect_secrets.sh][Detect-secrets][ERROR] No detect-secrets report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_detect_secrets.sh][ERROR] detect-secrets not found, skipping secret detection." | tee -a "$LOG_FILE"
  exit 1
fi
```

### 2. Create Processor Script
File: `scripts/detect_secrets_processor.py`

Template based on `gitleaks_processor.py`:
```python
#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

try:
    from scripts.llm_connector import llm_client
except ImportError:
    llm_client = None

def debug(msg):
    print(f"[detect_secrets_processor] {msg}", file=sys.stderr)

def detect_secrets_summary(detect_secrets_json):
    findings = []
    if detect_secrets_json and isinstance(detect_secrets_json, dict):
        results = detect_secrets_json.get('results', [])
        for r in results:
            finding = {
                'filename': r.get('filename', ''),
                'line_number': r.get('line_number', 0),
                'type': r.get('type', ''),
                'hashed_secret': r.get('hashed_secret', ''),
                'is_secret': r.get('is_secret', False),
                'is_verified': r.get('is_verified', False)
            }
            # Generate AI explanation if LLM is available
            prompt = f"Explain this secret detection finding: {finding['type']} in file {finding['filename']}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for detect-secrets finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    elif isinstance(detect_secrets_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(detect_secrets_json)
            if isinstance(data, dict):
                results = data.get('results', [])
                for r in results:
                    finding = {
                        'filename': r.get('filename', ''),
                        'line_number': r.get('line_number', 0),
                        'type': r.get('type', ''),
                        'hashed_secret': r.get('hashed_secret', ''),
                        'is_secret': r.get('is_secret', False),
                        'is_verified': r.get('is_verified', False)
                    }
                    prompt = f"Explain this secret detection finding: {finding['type']} in file {finding['filename']}"
                    try:
                        if llm_client:
                            finding['ai_explanation'] = llm_client.query(prompt)
                        else:
                            finding['ai_explanation'] = "LLM client not available."
                    except Exception as e:
                        debug(f"LLM query failed for detect-secrets finding: {e}")
                        finding['ai_explanation'] = "Error fetching AI explanation."
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse detect-secrets JSON as string.")
    else:
        debug("No detect-secrets results found in JSON.")
    return findings

def generate_detect_secrets_html_section(detect_secrets_findings):
    html_parts = []
    html_parts.append('<h2>Detect-secrets Secret Detection</h2>')
    if detect_secrets_findings:
        html_parts.append('<table><tr><th>Type</th><th>File</th><th>Line</th><th>Verified</th><th>AI Explanation</th></tr>')
        for finding in detect_secrets_findings:
            verified = 'Yes' if finding.get('is_verified', False) else 'No'
            icon = '🚨' if finding.get('is_verified', False) else '⚠️'
            type_escaped = html.escape(str(finding.get("type", "")))
            filename_escaped = html.escape(str(finding.get("filename", "")))
            line_escaped = html.escape(str(finding.get("line_number", "")))
            verified_escaped = html.escape(str(verified))
            ai_exp_escaped = html.escape(str(finding.get('ai_explanation', '')))
            
            html_parts.append(f'<tr><td>{type_escaped}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{icon} {verified_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)
```

### 3. Make Script Executable
```bash
chmod +x scripts/tools/run_detect_secrets.sh
chmod +x scripts/detect_secrets_processor.py
```

## Testing
1. Run script manually: `./scripts/tools/run_detect_secrets.sh`
2. Test processor with sample JSON: `python3 scripts/detect_secrets_processor.py`
3. Verify JSON parsing works correctly
4. Verify HTML generation works correctly
5. Test LLM integration (if available)

## Notes
- Follow existing GitLeaks and TruffleHog processor patterns
- Error handling should be comprehensive
- LLM integration is optional (graceful degradation)
- Use simple language, avoid forbidden terms

## Validation
After implementation:
1. Script should be executable: `test -x scripts/tools/run_detect_secrets.sh && echo "OK"`
2. Processor should parse JSON: Test with sample detect-secrets output
3. HTML generation should work: Test with sample findings
4. LLM integration should work (if configured): Test AI explanations

