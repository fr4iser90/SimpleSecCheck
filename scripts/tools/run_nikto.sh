#!/bin/bash
# Individual Nikto Scan Script for SimpleSecCheck

# Expected Environment Variables:
# ZAP_TARGET: Target URL to scan (e.g., http://host.docker.internal:8000)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
NIKTO_CONFIG_PATH="${NIKTO_CONFIG_PATH:-/SimpleSecCheck/nikto/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_nikto.sh] Initializing Nikto scan..." | tee -a "$LOG_FILE"

if command -v nikto &>/dev/null; then
  echo "[run_nikto.sh][Nikto] Running web server scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  
  NIKTO_JSON="$RESULTS_DIR/nikto.json"
  NIKTO_TEXT="$RESULTS_DIR/nikto.txt"
  
  # Run Nikto scan with JSON output
  echo "[run_nikto.sh][Nikto] Running web server scan..." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  nikto -h "$ZAP_TARGET" -Format json -output "$NIKTO_JSON" 2>/dev/null || {
    echo "[run_nikto.sh][Nikto] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  nikto -h "$ZAP_TARGET" -output "$NIKTO_TEXT" 2>/dev/null || {
    echo "[run_nikto.sh][Nikto] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$NIKTO_JSON" ] || [ -f "$NIKTO_TEXT" ]; then
    echo "[run_nikto.sh][Nikto] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$NIKTO_JSON" ] && echo "  - $NIKTO_JSON" | tee -a "$LOG_FILE"
    [ -f "$NIKTO_TEXT" ] && echo "  - $NIKTO_TEXT" | tee -a "$LOG_FILE"
    echo "[Nikto] Web server scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_nikto.sh][Nikto][ERROR] No Nikto report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_nikto.sh][ERROR] nikto not found, skipping web server scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Nikto is a core tool
fi


