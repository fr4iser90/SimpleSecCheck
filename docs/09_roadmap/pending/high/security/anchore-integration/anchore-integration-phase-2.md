# Anchore Integration – Phase 2: Core Implementation

## Overview
Create the Anchore execution script and processor to scan container images and generate reports.

## Objectives
- [ ] Create Anchore execution script
- [ ] Implement container image scanning
- [ ] Create Anchore results processor
- [ ] Generate HTML sections for reports

## Deliverables
- File: `scripts/tools/run_anchore.sh` - Anchore execution script
- File: `scripts/anchore_processor.py` - Anchore results processor
- JSON output: Anchore scan results
- HTML section: Anchore findings display

## Implementation Steps

### 1. Create Anchore Execution Script
**Location**: `scripts/tools/run_anchore.sh`  
**Action**: Create script following Trivy/Clair pattern

```bash
#!/bin/bash
# Individual Anchore Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to scan (container image name)
# RESULTS_DIR: Directory to store results
# LOG_FILE: Path to the main log file
# ANCHORE_CONFIG_PATH: Path to Anchore configuration file
# ANCHORE_IMAGE: Container image to scan

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
ANCHORE_CONFIG_PATH="${ANCHORE_CONFIG_PATH:-/SimpleSecCheck/anchore/config.yaml}"
ANCHORE_IMAGE="${ANCHORE_IMAGE:-}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_anchore.sh] Initializing Anchore scan..." | tee -a "$LOG_FILE"

if command -v grype &>/dev/null; then
  if [ -n "$ANCHORE_IMAGE" ]; then
    echo "[run_anchore.sh][Anchore] Running container image vulnerability scan on $ANCHORE_IMAGE..." | tee -a "$LOG_FILE"
    
    ANCHORE_JSON="$RESULTS_DIR/anchore.json"
    ANCHORE_TEXT="$RESULTS_DIR/anchore.txt"
    
    # Run Anchore Grype scan on container image
    echo "[run_anchore.sh][Anchore] Running container image vulnerability scan..." | tee -a "$LOG_FILE"
    
    grype --config "$ANCHORE_CONFIG_PATH" --output json "$ANCHORE_IMAGE" > "$ANCHORE_JSON" 2>>"$LOG_FILE" || {
      echo "[run_anchore.sh][Anchore] Scan failed, continuing..." | tee -a "$LOG_FILE"
    }
    
    # Generate text output
    grype --config "$ANCHORE_CONFIG_PATH" "$ANCHORE_IMAGE" > "$ANCHORE_TEXT" 2>>"$LOG_FILE" || {
      echo "[run_anchore.sh][Anchore] Text output generation failed, continuing..." | tee -a "$LOG_FILE"
    }
    
    echo "[run_anchore.sh][Anchore] Container image vulnerability scan complete." | tee -a "$LOG_FILE"
    
    if [ -f "$ANCHORE_JSON" ]; then
      echo "[run_anchore.sh][Anchore] Report(s) successfully generated:" | tee -a "$LOG_FILE"
      echo "  - $ANCHORE_JSON" | tee -a "$LOG_FILE"
      echo "[Anchore] Container image vulnerability scan complete." >> "$SUMMARY_TXT"
      exit 0
    else
      echo "[run_anchore.sh][Anchore][ERROR] No Anchore report was generated!" | tee -a "$LOG_FILE"
      exit 1
    fi
  else
    echo "[run_anchore.sh][WARNING] No container image specified, skipping Anchore scan." | tee -a "$LOG_FILE"
    echo "[Anchore] No container image specified, scan skipped." >> "$SUMMARY_TXT"
    exit 0
  fi
else
  echo "[run_anchore.sh][ERROR] grype not found, skipping container image vulnerability scan." | tee -a "$LOG_FILE"
  exit 1
fi
```

### 2. Create Anchore Processor
**Location**: `scripts/anchore_processor.py`  
**Action**: Create processor following clair_processor.py pattern

```python
#!/usr/bin/env python3
import sys

def debug(msg):
    print(f"[anchore_processor] {msg}", file=sys.stderr)

def anchore_summary(anchore_json):
    vulns = []
    if anchore_json and 'matches' in anchore_json:
        for match in anchore_json['matches']:
            vulns.append({
                'PkgName': match.get('artifact', {}).get('name', ''),
                'Severity': match.get('vulnerability', {}).get('severity', ''),
                'VulnerabilityID': match.get('vulnerability', {}).get('id', ''),
                'Title': match.get('vulnerability', {}).get('description', ''),
                'Description': match.get('vulnerability', {}).get('description', '')
            })
    else:
        debug("No Anchore results found in JSON.")
    return vulns

def generate_anchore_html_section(anchore_vulns):
    html_parts = []
    html_parts.append('<h2>Anchore Container Image Vulnerability Scan</h2>')
    
    # Check if there's a note about setup requirements
    if not anchore_vulns or (anchore_vulns and len(anchore_vulns) == 0):
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>')
    elif anchore_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in anchore_vulns:
            sev = v.get('Severity', 'UNKNOWN').upper()
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
                pkg_name_escaped = html.escape(str(v.get("PkgName", "")))
                sev_escaped = html.escape(str(sev))
                vuln_id_escaped = html.escape(str(v.get("VulnerabilityID", "")))
                title_escaped = html.escape(str(v.get("Title", "")))
            except ImportError:
                pkg_name_escaped = str(v.get("PkgName", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                vuln_id_escaped = str(v.get("VulnerabilityID", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(v.get("Title", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{pkg_name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{vuln_id_escaped}</td><td>{title_escaped}</td></tr>')
        html_parts.append('</table>')
    
    return "".join(html_parts)
```

### 3. Make Script Executable
**Action**: Ensure script has execute permissions

```bash
chmod +x scripts/tools/run_anchore.sh
```

## Dependencies
- Requires: Phase 1 (Foundation Setup)
- Blocks: Phase 3 (Integration & Testing)

## Estimated Time
2 hours

## Success Criteria
- [ ] Anchore script exists and is executable
- [ ] Script can scan Docker images
- [ ] JSON output is generated correctly
- [ ] Processor parses JSON correctly
- [ ] HTML section generation works
- [ ] Error handling is implemented
- [ ] Script follows Trivy/Clair patterns

## Testing
- [ ] Test script execution: `bash scripts/tools/run_anchore.sh`
- [ ] Test processor: `python3 -c "from scripts.anchore_processor import anchore_summary; print('OK')"`
- [ ] Test with sample Docker image: `grype alpine:latest`
- [ ] Verify JSON parsing works with generated output

## Notes
- Follow existing patterns from Trivy and Clair processors
- Anchore JSON format differs from Trivy/Clair, so parser needs adjustment
- HTML generation should match existing report styles
- Error handling should be comprehensive

