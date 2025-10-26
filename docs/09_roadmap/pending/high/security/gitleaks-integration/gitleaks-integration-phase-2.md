# GitLeaks Integration – Phase 2: Core Implementation

## Overview
Create the GitLeaks execution script and results processor to scan repositories and generate formatted output.

## Objectives
- [ ] Create `scripts/tools/run_gitleaks.sh` script
- [ ] Create `scripts/gitleaks_processor.py` processor
- [ ] Implement JSON and text report generation
- [ ] Add LLM explanations for findings

## Deliverables
- File: `scripts/tools/run_gitleaks.sh` - GitLeaks execution script
- File: `scripts/gitleaks_processor.py` - GitLeaks results processor
- Tests: Script execution on sample repository

## Implementation Steps

### Step 1: Create run_gitleaks.sh
Create `scripts/tools/run_gitleaks.sh` following the TruffleHog pattern:

```bash
#!/bin/bash
# Individual GitLeaks Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
GITLEAKS_CONFIG_PATH="${GITLEAKS_CONFIG_PATH:-/SimpleSecCheck/gitleaks/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_gitleaks.sh] Initializing GitLeaks scan..." | tee -a "$LOG_FILE"

if command -v gitleaks &>/dev/null; then
  echo "[run_gitleaks.sh][GitLeaks] Running secret detection scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  GITLEAKS_JSON="$RESULTS_DIR/gitleaks.json"
  GITLEAKS_TEXT="$RESULTS_DIR/gitleaks.txt"
  
  # Run GitLeaks scan with JSON output
  echo "[run_gitleaks.sh][GitLeaks] Running secret detection scan..." | tee -a "$LOG_FILE"
  gitleaks detect --source "$TARGET_PATH" --config-path "$GITLEAKS_CONFIG_PATH" --report-path "$GITLEAKS_JSON" --no-git 2>>"$LOG_FILE" || {
    echo "[run_gitleaks.sh][GitLeaks] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  echo "[run_gitleaks.sh][GitLeaks] Running text report generation..." | tee -a "$LOG_FILE"
  gitleaks detect --source "$TARGET_PATH" --config-path "$GITLEAKS_CONFIG_PATH" --report-path "$GITLEAKS_TEXT" --no-git --verbose 2>>"$LOG_FILE" || {
    echo "[run_gitleaks.sh][GitLeaks] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$GITLEAKS_JSON" ] || [ -f "$GITLEAKS_TEXT" ]; then
    echo "[run_gitleaks.sh][GitLeaks] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$GITLEAKS_JSON" ] && echo "  - $GITLEAKS_JSON" | tee -a "$LOG_FILE"
    [ -f "$GITLEAKS_TEXT" ] && echo "  - $GITLEAKS_TEXT" | tee -a "$LOG_FILE"
    echo "[GitLeaks] Secret detection scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_gitleaks.sh][GitLeaks][ERROR] No GitLeaks report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_gitleaks.sh][ERROR] gitleaks not found, skipping secret detection." | tee -a "$LOG_FILE"
  exit 1
fi
```

### Step 2: Create gitleaks_processor.py
Create `scripts/gitleaks_processor.py` to parse and format results:

```python
#!/usr/bin/env python3
import sys
import html
import json

sys.path.insert(0, '/SimpleSecCheck')

try:
    from scripts.llm_connector import llm_client
except ImportError:
    llm_client = None

def debug(msg):
    print(f"[gitleaks_processor] {msg}", file=sys.stderr)

def gitleaks_summary(gitleaks_json):
    findings = []
    if gitleaks_json and isinstance(gitleaks_json, list):
        for r in gitleaks_json:
            finding = {
                'rule_id': r.get('RuleID', ''),
                'description': r.get('Description', ''),
                'file': r.get('File', ''),
                'line': r.get('Line', 0),
                'secret': r.get('Secret', ''),
                'author': r.get('Author', ''),
                'commit': r.get('Commit', '')
            }
            # Generate AI explanation if LLM is available
            prompt = f"Explain this secret detection finding: {finding['rule_id']} - {finding['description']}"
            try:
                if llm_client:
                    finding['ai_explanation'] = llm_client.query(prompt)
                else:
                    finding['ai_explanation'] = "LLM client not available."
            except Exception as e:
                debug(f"LLM query failed for GitLeaks finding: {e}")
                finding['ai_explanation'] = "Error fetching AI explanation."
            findings.append(finding)
    elif gitleaks_json and isinstance(gitleaks_json, str):
        try:
            data = json.loads(gitleaks_json)
            if isinstance(data, list):
                for r in data:
                    finding = {
                        'rule_id': r.get('RuleID', ''),
                        'description': r.get('Description', ''),
                        'file': r.get('File', ''),
                        'line': r.get('Line', 0),
                        'secret': r.get('Secret', ''),
                        'author': r.get('Author', ''),
                        'commit': r.get('Commit', '')
                    }
                    prompt = f"Explain this secret detection finding: {finding['rule_id']} - {finding['description']}"
                    try:
                        if llm_client:
                            finding['ai_explanation'] = llm_client.query(prompt)
                        else:
                            finding['ai_explanation'] = "LLM client not available."
                    except Exception as e:
                        debug(f"LLM query failed for GitLeaks finding: {e}")
                        finding['ai_explanation'] = "Error fetching AI explanation."
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse GitLeaks JSON as string.")
    else:
        debug("No GitLeaks results found in JSON.")
    return findings

def generate_gitleaks_html_section(gitleaks_findings):
    html_parts = []
    html_parts.append('<h2>GitLeaks Secret Detection</h2>')
    if gitleaks_findings:
        html_parts.append('<table><tr><th>Rule ID</th><th>File</th><th>Line</th><th>Description</th><th>AI Explanation</th></tr>')
        for finding in gitleaks_findings:
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            file_escaped = html.escape(str(finding.get("file", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            description_escaped = html.escape(str(finding.get("description", "")))
            ai_exp_escaped = html.escape(str(finding.get('ai_explanation', '')))
            
            html_parts.append(f'<tr><td>{rule_id_escaped}</td><td>{file_escaped}</td><td>{line_escaped}</td><td>{description_escaped}</td><td>{ai_exp_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)
```

### Step 3: Make Scripts Executable
```bash
chmod +x scripts/tools/run_gitleaks.sh
```

## Dependencies
- Requires: Phase 1 completion (GitLeaks installed)
- Blocks: Phase 3 - Integration & Testing

## Estimated Time
2 hours

## Success Criteria
- [ ] run_gitleaks.sh successfully executes GitLeaks scans
- [ ] gitleaks_processor.py correctly parses JSON output
- [ ] HTML sections are generated with proper formatting
- [ ] LLM explanations are included when available
- [ ] Scripts handle errors gracefully
- [ ] Both JSON and text reports are generated

## Testing
- Test run_gitleaks.sh on a sample repository
- Verify JSON and text output files are created
- Test processor with sample GitLeaks JSON
- Verify HTML section generation
- Test error handling with missing files

