#!/bin/bash
# Individual Wapiti Scan Script for SimpleSecCheck

# Expected Environment Variables:
# ZAP_TARGET: Target URL to scan (e.g., http://host.docker.internal:8000)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
WAPITI_CONFIG_PATH="${WAPITI_CONFIG_PATH:-/SimpleSecCheck/wapiti/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_wapiti.sh] Initializing Wapiti scan..." | tee -a "$LOG_FILE"

if command -v wapiti &>/dev/null; then
  echo "[run_wapiti.sh][Wapiti] Running web vulnerability scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  
  WAPITI_JSON="$RESULTS_DIR/wapiti.json"
  WAPITI_TEXT="$RESULTS_DIR/wapiti.txt"
  
  # Run Wapiti scan with JSON output
  echo "[run_wapiti.sh][Wapiti] Running web vulnerability scan..." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  wapiti -u "$ZAP_TARGET" -f json -o "$WAPITI_JSON" 2>/dev/null || {
    echo "[run_wapiti.sh][Wapiti] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  wapiti -u "$ZAP_TARGET" -o "$WAPITI_TEXT" 2>/dev/null || {
    echo "[run_wapiti.sh][Wapiti] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$WAPITI_JSON" ] || [ -f "$WAPITI_TEXT" ]; then
    echo "[run_wapiti.sh][Wapiti] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$WAPITI_JSON" ] && echo "  - $WAPITI_JSON" | tee -a "$LOG_FILE"
    [ -f "$WAPITI_TEXT" ] && echo "  - $WAPITI_TEXT" | tee -a "$LOG_FILE"
    echo "[Wapiti] Web vulnerability scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_wapiti.sh][Wapiti][ERROR] No Wapiti report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_wapiti.sh][ERROR] wapiti not found, skipping web vulnerability scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Wapiti is a core tool
fi

