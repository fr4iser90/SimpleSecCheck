#!/bin/bash
# Individual Brakeman Scan Script for SimpleSecCheck

# Expected Environment Variables:
# TARGET_PATH: Path to target directory (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# BRAKEMAN_CONFIG_PATH: Path to Brakeman configuration file

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
BRAKEMAN_CONFIG_PATH="${BRAKEMAN_CONFIG_PATH:-/SimpleSecCheck/brakeman/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_brakeman.sh] Initializing Brakeman scan..." | tee -a "$LOG_FILE"

if command -v brakeman &>/dev/null; then
  echo "[run_brakeman.sh][Brakeman] Running Ruby on Rails security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  BRAKEMAN_JSON="$RESULTS_DIR/brakeman.json"
  BRAKEMAN_TEXT="$RESULTS_DIR/brakeman.txt"
  
  # Check for Ruby/Rails files
  RUBY_FILES=()
  
  # Look for common Ruby/Rails files
  for pattern in "*.rb" "Gemfile" "config/application.rb"; do
    while IFS= read -r -d '' file; do
      RUBY_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#RUBY_FILES[@]} -eq 0 ]; then
    echo "[run_brakeman.sh][Brakeman] No Ruby/Rails files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_brakeman.sh][Brakeman] Found ${#RUBY_FILES[@]} Ruby/Rails file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report with --force to scan anyway
  if brakeman -q -f json -o "$BRAKEMAN_JSON" --force "$TARGET_PATH" 2>/dev/null; then
    echo "[run_brakeman.sh][Brakeman] JSON report generation completed." | tee -a "$LOG_FILE"
  else
    echo "[run_brakeman.sh][Brakeman] JSON report generation failed." >> "$LOG_FILE"
  fi
  
  # Generate text report (without format option, outputs plaintext by default) with --force
  if brakeman -q -o "$BRAKEMAN_TEXT" --force "$TARGET_PATH" 2>/dev/null; then
    echo "[run_brakeman.sh][Brakeman] Text report generation completed." | tee -a "$LOG_FILE"
  else
    echo "[run_brakeman.sh][Brakeman] Text report generation failed." >> "$LOG_FILE"
  fi
  
  if [ -f "$BRAKEMAN_JSON" ] || [ -f "$BRAKEMAN_TEXT" ]; then
    echo "[run_brakeman.sh][Brakeman] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$BRAKEMAN_JSON" ] && echo "  - $BRAKEMAN_JSON" | tee -a "$LOG_FILE"
    [ -f "$BRAKEMAN_TEXT" ] && echo "  - $BRAKEMAN_TEXT" | tee -a "$LOG_FILE"
    echo "[Brakeman] Ruby on Rails security scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_brakeman.sh][Brakeman][ERROR] No Brakeman report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_brakeman.sh][ERROR] Brakeman not found, skipping Ruby security scan." | tee -a "$LOG_FILE"
  exit 1
fi

