#!/bin/bash
# Individual Trivy Scan Script for SecuLite Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to scan (e.g., /target for filesystem, or image name)
# RESULTS_DIR: Directory to store results (e.g., /seculite/results)
# LOG_FILE: Path to the main log file (e.g., /seculite/logs/security-check.log)
# TRIVY_SCAN_TYPE: Type of scan, e.g., 'fs' for filesystem, 'image' for image. Defaults to 'fs'.
# TRIVY_CONFIG_PATH: Path to Trivy configuration file.

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/seculite/results}"
LOG_FILE="${LOG_FILE:-/seculite/logs/security-check.log}"
TRIVY_SCAN_TYPE="${TRIVY_SCAN_TYPE:-fs}"
TRIVY_CONFIG_PATH="${TRIVY_CONFIG_PATH:-/seculite/trivy/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_trivy.sh] Initializing Trivy scan..." | tee -a "$LOG_FILE"

if command -v trivy &>/dev/null; then
  echo "[run_trivy.sh][Trivy] Running $TRIVY_SCAN_TYPE scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  TRIVY_JSON="$RESULTS_DIR/trivy.json"
  TRIVY_TEXT="$RESULTS_DIR/trivy.txt"
  
  trivy "$TRIVY_SCAN_TYPE" --config "$TRIVY_CONFIG_PATH" --format json -o "$TRIVY_JSON" "$TARGET_PATH" 2>>"$LOG_FILE" || {
    echo "[run_trivy.sh][Trivy] JSON report generation failed." >> "$LOG_FILE"
  }
  trivy "$TRIVY_SCAN_TYPE" --config "$TRIVY_CONFIG_PATH" --format table -o "$TRIVY_TEXT" "$TARGET_PATH" 2>>"$LOG_FILE" || {
    echo "[run_trivy.sh][Trivy] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$TRIVY_JSON" ] || [ -f "$TRIVY_TEXT" ]; then
    echo "[run_trivy.sh][Trivy] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$TRIVY_JSON" ] && echo "  - $TRIVY_JSON" | tee -a "$LOG_FILE"
    [ -f "$TRIVY_TEXT" ] && echo "  - $TRIVY_TEXT" | tee -a "$LOG_FILE"
    echo "[Trivy] Dependency/container scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_trivy.sh][Trivy][ERROR] No Trivy report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_trivy.sh][ERROR] trivy not found, skipping dependency/container scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Trivy is a core tool
fi 