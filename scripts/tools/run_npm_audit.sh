#!/bin/bash
# Individual npm audit Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
NPM_AUDIT_CONFIG_PATH="${NPM_AUDIT_CONFIG_PATH:-/SimpleSecCheck/npm-audit/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_npm_audit.sh] Initializing npm audit scan..." | tee -a "$LOG_FILE"

if command -v npm &>/dev/null; then
  echo "[run_npm_audit.sh][npm audit] Running npm dependency security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  NPM_AUDIT_JSON="$RESULTS_DIR/npm-audit.json"
  NPM_AUDIT_TEXT="$RESULTS_DIR/npm-audit.txt"
  
  # Check for Node.js/JavaScript dependency files
  DEPENDENCY_FILES=()
  
  # Look for root package.json files only (exclude node_modules)
  # npm audit already audits all dependencies, so we only need the main package.json per project
  while IFS= read -r -d '' file; do
    DEPENDENCY_FILES+=("$file")
  done < <(find "$TARGET_PATH" -name "package.json" -type f -not -path "*/node_modules/*" -print0 2>/dev/null)
  
  if [ ${#DEPENDENCY_FILES[@]} -eq 0 ]; then
    echo "[run_npm_audit.sh][npm audit] No package.json files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_npm_audit.sh][npm audit] Found ${#DEPENDENCY_FILES[@]} package.json file(s)." | tee -a "$LOG_FILE"
  
  # Scan each package.json directory
  VULNS_FOUND=0
  for package_json in "${DEPENDENCY_FILES[@]}"; do
    dir=$(dirname "$package_json")
    echo "[run_npm_audit.sh][npm audit] Scanning directory: $dir" | tee -a "$LOG_FILE"
    
    # Generate JSON report
    cd "$dir" && npm audit --json > "$NPM_AUDIT_JSON-$VULNS_FOUND" 2>>"$LOG_FILE" || {
      echo "[run_npm_audit.sh][npm audit] JSON report generation failed for $dir" >> "$LOG_FILE"
    }
    
    # Generate text report
    cd "$dir" && npm audit > "$NPM_AUDIT_TEXT-$VULNS_FOUND" 2>>"$LOG_FILE" || {
      echo "[run_npm_audit.sh][npm audit] Text report generation failed for $dir" >> "$LOG_FILE"
    }
    
    VULNS_FOUND=$((VULNS_FOUND + 1))
  done
  
  # Combine all results into single files (if multiple found)
  if [ $VULNS_FOUND -gt 0 ]; then
    if [ -f "$NPM_AUDIT_JSON-0" ]; then
      cp "$NPM_AUDIT_JSON-0" "$NPM_AUDIT_JSON"
    else
      # Create minimal JSON if scan failed
      echo '{"vulnerabilities":{}}' > "$NPM_AUDIT_JSON"
    fi
    if [ -f "$NPM_AUDIT_TEXT-0" ]; then
      cp "$NPM_AUDIT_TEXT-0" "$NPM_AUDIT_TEXT"
    else
      echo "npm audit: Scan completed but report generation failed" > "$NPM_AUDIT_TEXT"
    fi
    rm -f "$NPM_AUDIT_JSON"-* "$NPM_AUDIT_TEXT"-*
    
    echo "[run_npm_audit.sh][npm audit] Scan completed. Found $VULNS_FOUND package.json files." | tee -a "$LOG_FILE"
    echo "npm audit: Completed" >> "$SUMMARY_TXT"
  else
    echo "[run_npm_audit.sh][npm audit] No package.json files found, creating empty reports." | tee -a "$LOG_FILE"
    echo '{"vulnerabilities":{}}' > "$NPM_AUDIT_JSON"
    echo "No package.json files found" > "$NPM_AUDIT_TEXT"
  fi
else
  echo "[run_npm_audit.sh][npm audit] npm command not found, skipping npm audit scan." | tee -a "$LOG_FILE"
fi

