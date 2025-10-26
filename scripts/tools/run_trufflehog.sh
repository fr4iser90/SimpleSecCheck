#!/bin/bash
# Individual TruffleHog Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# TRUFFLEHOG_CONFIG_PATH: Path to TruffleHog configuration file.

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
  
  # Run secret detection scan with JSON output (without --config to avoid protobuf issues)
  echo "[run_trufflehog.sh][TruffleHog] Running secret detection scan..." | tee -a "$LOG_FILE"
  trufflehog filesystem --json "$TARGET_PATH" > "$TRUFFLEHOG_JSON" 2>>"$LOG_FILE" || {
    echo "[run_trufflehog.sh][TruffleHog] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report (without --config to avoid protobuf issues)
  echo "[run_trufflehog.sh][TruffleHog] Running text report generation..." | tee -a "$LOG_FILE"
  trufflehog filesystem "$TARGET_PATH" > "$TRUFFLEHOG_TEXT" 2>>"$LOG_FILE" || {
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
