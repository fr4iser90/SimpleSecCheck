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
  detect-secrets scan --all-files "$TARGET_PATH" > "$DETECT_SECRETS_JSON" 2>>"$LOG_FILE" || {
    echo "[run_detect_secrets.sh][Detect-secrets] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  echo "[run_detect_secrets.sh][Detect-secrets] Running text report generation..." | tee -a "$LOG_FILE"
  detect-secrets scan --all-files "$TARGET_PATH" > "$DETECT_SECRETS_TEXT" 2>>"$LOG_FILE" || {
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

