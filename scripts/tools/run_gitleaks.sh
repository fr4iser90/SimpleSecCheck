#!/bin/bash
# Individual GitLeaks Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# GITLEAKS_CONFIG_PATH: Path to GitLeaks configuration file.

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
  
  # Run secret detection scan with JSON output
  echo "[run_gitleaks.sh][GitLeaks] Running secret detection scan..." | tee -a "$LOG_FILE"
  gitleaks detect --source "$TARGET_PATH" --report-path "$GITLEAKS_JSON" --no-git 2>>"$LOG_FILE" || {
    echo "[run_gitleaks.sh][GitLeaks] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  echo "[run_gitleaks.sh][GitLeaks] Running text report generation..." | tee -a "$LOG_FILE"
  gitleaks detect --source "$TARGET_PATH" --report-path "$GITLEAKS_TEXT" --no-git --verbose 2>>"$LOG_FILE" || {
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

