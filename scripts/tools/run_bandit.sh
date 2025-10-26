#!/bin/bash
# Individual Bandit Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
BANDIT_CONFIG_PATH="${BANDIT_CONFIG_PATH:-/SimpleSecCheck/bandit/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_bandit.sh] Initializing Bandit scan..." | tee -a "$LOG_FILE"

if command -v bandit &>/dev/null; then
  echo "[run_bandit.sh][Bandit] Running Python security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  BANDIT_JSON="$RESULTS_DIR/bandit.json"
  BANDIT_TEXT="$RESULTS_DIR/bandit.txt"
  
  # Find Python files to scan
  PYTHON_FILES=$(find "$TARGET_PATH" -name "*.py" -type f 2>/dev/null | wc -l)
  
  if [ "$PYTHON_FILES" -eq 0 ]; then
    echo "[run_bandit.sh][Bandit] No Python files found in $TARGET_PATH" | tee -a "$LOG_FILE"
    echo "[run_bandit.sh][Bandit] Creating empty reports..." | tee -a "$LOG_FILE"
    
    # Create empty JSON report
    echo '{"generated_at": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "metrics": {"_totals": {"loc": 0, "nosec": 0, "skipped_tests": 0, "tests": 0}}, "results": []}' > "$BANDIT_JSON"
    
    # Create empty text report
    echo "Bandit Scan Results" > "$BANDIT_TEXT"
    echo "===================" >> "$BANDIT_TEXT"
    echo "No Python files found." >> "$BANDIT_TEXT"
    echo "Scan completed at: $(date)" >> "$BANDIT_TEXT"
    
    echo "[Bandit] No Python files found." >> "$SUMMARY_TXT"
    exit 0
  fi
  
  echo "[run_bandit.sh][Bandit] Found $PYTHON_FILES Python file(s) to scan..." | tee -a "$LOG_FILE"
  
  # Run Bandit scan with JSON output
  bandit -r "$TARGET_PATH" -f json -o "$BANDIT_JSON" 2>/dev/null || {
    echo "[run_bandit.sh][Bandit] JSON report generation encountered issues." >> "$LOG_FILE"
  }
  
  # Run Bandit scan with text output
  bandit -r "$TARGET_PATH" > "$BANDIT_TEXT" 2>/dev/null || {
    echo "[run_bandit.sh][Bandit] Text report generation encountered issues." >> "$LOG_FILE"
  }
  
  if [ -f "$BANDIT_JSON" ] || [ -f "$BANDIT_TEXT" ]; then
    echo "[run_bandit.sh][Bandit] Bandit scan completed successfully." | tee -a "$LOG_FILE"
    echo "Bandit scan completed - see $BANDIT_JSON and $BANDIT_TEXT" >> "$SUMMARY_TXT"
  else
    echo "[run_bandit.sh][Bandit] No Bandit results generated." | tee -a "$LOG_FILE"
    echo "Bandit scan failed - no results generated" >> "$SUMMARY_TXT"
  fi
else
  echo "[run_bandit.sh][Bandit] Bandit CLI not found. Skipping Bandit scan." | tee -a "$LOG_FILE"
  echo "Bandit scan skipped - CLI not available" >> "$SUMMARY_TXT"
fi

echo "[run_bandit.sh] Bandit scan orchestration completed." | tee -a "$LOG_FILE"

