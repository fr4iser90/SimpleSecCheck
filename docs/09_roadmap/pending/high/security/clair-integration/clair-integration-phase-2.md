# Clair Integration – Phase 2: Core Implementation

## Overview
Create the core components for Clair integration: the execution script and the results processor. Implement container image vulnerability scanning, result parsing, and HTML report generation with LLM explanation support.

## Objectives
- [ ] Create: `scripts/tools/run_clair.sh`
- [ ] Implement Clair container image scanning script
- [ ] Support JSON output format
- [ ] Generate text reports
- [ ] Create: `scripts/clair_processor.py`
- [ ] Parse Clair JSON results
- [ ] Generate HTML sections for reports
- [ ] Integrate with LLM explanations

## Deliverables
- File: `scripts/tools/run_clair.sh` - Execution script for Clair
- File: `scripts/clair_processor.py` - Results processor with LLM support

## Dependencies
- Requires: Phase 1 completion (Clair installation and configuration)
- Blocks: Phase 3 (Integration & Testing)

## Estimated Time
2 hours

## Success Criteria
- [ ] `run_clair.sh` script is executable
- [ ] Script handles environment variables correctly
- [ ] Script generates JSON and text reports
- [ ] Script logs output to central log file
- [ ] `clair_processor.py` parses JSON correctly
- [ ] Processor generates HTML sections properly
- [ ] LLM explanations are generated for findings
- [ ] Processor handles errors gracefully

## Implementation Details

### 1. Create Execution Script
File: `scripts/tools/run_clair.sh`

Template based on `run_trivy.sh`:
```bash
#!/bin/bash
# Individual Clair Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to scan (container image name or Docker image)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# CLAIR_CONFIG_PATH: Path to Clair configuration file.
# CLAIR_IMAGE: Container image to scan (e.g., alpine:latest)

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
CLAIR_CONFIG_PATH="${CLAIR_CONFIG_PATH:-/SimpleSecCheck/clair/config.yaml}"
CLAIR_IMAGE="${CLAIR_IMAGE:-}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_clair.sh] Initializing Clair scan..." | tee -a "$LOG_FILE"

if command -v clair &>/dev/null; then
  if [ -n "$CLAIR_IMAGE" ]; then
    echo "[run_clair.sh][Clair] Running container image vulnerability scan on $CLAIR_IMAGE..." | tee -a "$LOG_FILE"
    
    CLAIR_JSON="$RESULTS_DIR/clair.json"
    CLAIR_TEXT="$RESULTS_DIR/clair.txt"
    
    # Run Clair scan on container image
    echo "[run_clair.sh][Clair] Running container image vulnerability scan..." | tee -a "$LOG_FILE"
    clair --config "$CLAIR_CONFIG_PATH" scan --image "$CLAIR_IMAGE" --format json > "$CLAIR_JSON" 2>>"$LOG_FILE" || {
      echo "[run_clair.sh][Clair] JSON report generation failed." >> "$LOG_FILE"
    }
    
    # Generate text report
    echo "[run_clair.sh][Clair] Running text report generation..." | tee -a "$LOG_FILE"
    clair --config "$CLAIR_CONFIG_PATH" scan --image "$CLAIR_IMAGE" --format table > "$CLAIR_TEXT" 2>>"$LOG_FILE" || {
      echo "[run_clair.sh][Clair] Text report generation failed." >> "$LOG_FILE"
    }

    if [ -f "$CLAIR_JSON" ] || [ -f "$CLAIR_TEXT" ]; then
      echo "[run_clair.sh][Clair] Report(s) successfully generated:" | tee -a "$LOG_FILE"
      [ -f "$CLAIR_JSON" ] && echo "  - $CLAIR_JSON" | tee -a "$LOG_FILE"
      [ -f "$CLAIR_TEXT" ] && echo "  - $CLAIR_TEXT" | tee -a "$LOG_FILE"
      echo "[Clair] Container image vulnerability scan complete." >> "$SUMMARY_TXT"
      exit 0
    else
      echo "[run_clair.sh][Clair][ERROR] No Clair report was generated!" | tee -a "$LOG_FILE"
      exit 1
    fi
  else
    echo "[run_clair.sh][WARNING] No container image specified, skipping Clair scan." | tee -a "$LOG_FILE"
    echo "[Clair] No container image specified, scan skipped." >> "$SUMMARY_TXT"
    exit 0
  fi
else
  echo "[run_clair.sh][ERROR] clair not found, skipping container image vulnerability scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### 2. Create Processor Script
File: `scripts/clair_processor.py`

Template based on `trivy_processor.py`:
```python
#!/usr/bin/env python3
import sys

def debug(msg):
    print(f"[clair_processor] {msg}", file=sys.stderr)

def clair_summary(clair_json):
    vulns = []
    if clair_json and 'vulnerabilities' in clair_json:
        for v in clair_json['vulnerabilities']:
            vulns.append({
                'PkgName': v.get('package', ''),
                'Severity': v.get('severity', ''),
                'VulnerabilityID': v.get('vulnerability', ''),
                'Title': v.get('title', ''),
                'Description': v.get('description', '')
            })
    else:
        debug("No Clair results found in JSON.")
    return vulns

def generate_clair_html_section(clair_vulns):
    html_parts = []
    html_parts.append('<h2>Clair Container Image Vulnerability Scan</h2>')
    if clair_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in clair_vulns:
            sev = v['Severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            # Basic HTML escaping
            pkg_name_escaped = sev_escaped = vuln_id_escaped = title_escaped = ""
            try:
                import html
                pkg_name_escaped = html.escape(str(v["PkgName"]))
                sev_escaped = html.escape(str(sev))
                vuln_id_escaped = html.escape(str(v["VulnerabilityID"]))
                title_escaped = html.escape(str(v["Title"]))
            except ImportError:
                pkg_name_escaped = str(v["PkgName"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                vuln_id_escaped = str(v["VulnerabilityID"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(v["Title"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{pkg_name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{vuln_id_escaped}</td><td>{title_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>')
    return "".join(html_parts)
```

### 3. Make Script Executable
```bash
chmod +x scripts/tools/run_clair.sh
chmod +x scripts/clair_processor.py
```

## Testing
1. Run script manually: `./scripts/tools/run_clair.sh`
2. Test processor with sample JSON: `python3 scripts/clair_processor.py`
3. Verify JSON parsing works correctly
4. Verify HTML generation works correctly
5. Test LLM integration (if available)

## Notes
- Follow existing Trivy container scanning processor patterns
- Error handling should be comprehensive
- LLM integration is optional (graceful degradation)
- Use simple language, avoid forbidden terms
- Clair requires container image name as input (not filesystem path)

## Validation
After implementation:
1. Script should be executable: `test -x scripts/tools/run_clair.sh && echo "OK"`
2. Processor should parse JSON: Test with sample Clair output
3. HTML generation should work: Test with sample findings
4. LLM integration should work (if configured): Test AI explanations

## Integration with LLM
To add LLM explanations to the processor:

```python
sys.path.insert(0, '/SimpleSecCheck')

try:
    from scripts.llm_connector import llm_client
except ImportError:
    llm_client = None

# In the summary function, add:
# prompt = f"Explain this vulnerability: {v['Title']} with severity {v['Severity']}"
# try:
#     if llm_client:
#         v['ai_explanation'] = llm_client.query(prompt)
#     else:
#         v['ai_explanation'] = "LLM client not available."
# except Exception as e:
#     debug(f"LLM query failed: {e}")
#     v['ai_explanation'] = "Error fetching AI explanation."
```

## Alternative: Use Clair Core
If full Clair is too complex, consider using Clair Core which is simpler:
- No PostgreSQL database requirement
- Single binary installation
- Simpler configuration
- Compatible with same scanning approach

