# TruffleHog Integration – Phase 2: Core Implementation

## 📋 Phase Overview
- **Phase Number**: 2
- **Phase Name**: Core Implementation
- **Estimated Time**: 2 hours
- **Status**: Planning
- **Progress**: 0%
- **Created**: 2025-10-26T00:18:41.000Z

## 🎯 Phase Objectives
Create TruffleHog execution script and processor for secret detection scanning.

## 📊 Detailed Tasks

### Task 2.1: Execution Script Creation (1 hour)
- [ ] **2.1.1** Create `scripts/tools/run_trufflehog.sh`
- [ ] **2.1.2** Implement secret detection scanning with JSON output
- [ ] **2.1.3** Implement text output generation
- [ ] **2.1.4** Add error handling and logging

### Task 2.2: Processor Creation (1 hour)
- [ ] **2.2.1** Create `scripts/trufflehog_processor.py`
- [ ] **2.2.2** Parse TruffleHog JSON results
- [ ] **2.2.3** Generate HTML sections for reports
- [ ] **2.2.4** Integrate with LLM explanations

## 🔧 Technical Implementation Details

### Execution Script Pattern (run_trufflehog.sh)
```bash
#!/bin/bash
# Individual TruffleHog Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
TRUFFLEHOG_CONFIG_PATH="${TRUFFLEHOG_CONFIG_PATH:-/SimpleSecCheck/trufflehog/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_trufflehog.sh] Initializing TruffleHog scan..." | tee -a "$LOG_FILE"

if command -v trufflehog &>/dev/null; then
  echo "[run_trufflehog.sh][TruffleHog] Running secret detection scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  TRUFFLEHOG_JSON="$RESULTS_DIR/trufflehog.json"
  TRUFFLEHOG_TEXT="$RESULTS_DIR/trufflehog.txt"
  
  # Run secret detection scan
  trufflehog filesystem --json --config="$TRUFFLEHOG_CONFIG_PATH" "$TARGET_PATH" -o "$TRUFFLEHOG_JSON" 2>>"$LOG_FILE" || {
    echo "[run_trufflehog.sh][TruffleHog] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  trufflehog filesystem --config="$TRUFFLEHOG_CONFIG_PATH" "$TARGET_PATH" > "$TRUFFLEHOG_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_trufflehog.sh][TruffleHog] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$TRUFFLEHOG_JSON" ] || [ -f "$TRUFFLEHOG_TEXT" ]; then
    echo "[run_trufflehog.sh][TruffleHog] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$TRUFFLEHOG_JSON" ] && echo "  - $TRUFFLEHOG_JSON" | tee -a "$LOG_FILE"
    [ -f "$TRUFFLEHOG_TEXT" ] && echo "  - $TRUFFLEHOG_TEXT" | tee -a "$LOG_FILE"
    echo "[TruffleHog] Secret detection scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_trufflehog.sh][TruffleHog][ERROR] No TruffleHog report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_trufflehog.sh][ERROR] trufflehog not found, skipping secret detection." | tee -a "$LOG_FILE"
  exit 1
fi
```

### Processor Pattern (trufflehog_processor.py)
```python
#!/usr/bin/env python3
import sys
import html
from scripts.llm_connector import llm_client

def debug(msg):
    print(f"[trufflehog_processor] {msg}", file=sys.stderr)

def trufflehog_summary(trufflehog_json):
    findings = []
    if trufflehog_json and isinstance(trufflehog_json, list):
        for r in trufflehog_json:
            finding = {
                'detector': r.get('DetectorName', ''),
                'verified': r.get('Verified', False),
                'raw': r.get('Raw', ''),
                'redacted': r.get('Redacted', ''),
                'extra_data': r.get('ExtraData', {}),
                'source_metadata': r.get('SourceMetadata', {})
            }
            prompt = f"Explain this secret detection finding: {finding['detector']} - {finding.get('extra_data', {}).get('message', '')}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for TruffleHog finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    else:
        debug("No TruffleHog results found in JSON.")
    return findings

def generate_trufflehog_html_section(trufflehog_findings):
    html_parts = []
    html_parts.append('<h2>TruffleHog Secret Detection</h2>')
    if trufflehog_findings:
        html_parts.append('<table><tr><th>Detector</th><th>Verified</th><th>Details</th><th>AI Explanation</th></tr>')
        for finding in trufflehog_findings:
            verified = 'Yes' if finding.get('verified', False) else 'No'
            icon = '🚨' if finding.get('verified', False) else '⚠️'
            detector_escaped = html.escape(str(finding.get("detector", "")))
            verified_escaped = html.escape(str(verified))
            details_escaped = html.escape(str(finding.get("extra_data", {}).get("message", "")))
            ai_exp_escaped = html.escape(str(finding.get('ai_explanation', '')))
            
            html_parts.append(f'<tr><td>{detector_escaped}</td><td>{icon} {verified_escaped}</td><td>{details_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)
```

## 📦 Deliverables
- File: `scripts/tools/run_trufflehog.sh` - Execution script
- File: `scripts/trufflehog_processor.py` - Result processor

## 🔗 Dependencies
- Requires: Phase 1 (Foundation Setup) completed
- Blocks: Phase 3 (Integration & Testing)

## ⏱️ Estimated Time
2 hours

## ✅ Success Criteria
- [ ] run_trufflehog.sh created and executable
- [ ] Script generates JSON and text reports
- [ ] trufflehog_processor.py created with proper parsing
- [ ] HTML section generation works correctly
- [ ] LLM integration functional
- [ ] Individual components tested with sample code

## 📝 Notes
- Follow patterns from existing tool scripts (run_semgrep.sh, run_codeql.sh)
- Follow patterns from existing processors (nuclei_processor.py, semgrep_processor.py)
- Ensure proper error handling and logging
- Test with code samples containing hardcoded secrets

