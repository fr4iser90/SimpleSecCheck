#!/bin/bash
# Anchore Scan Script for SimpleSecCheck Plugin System

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
    
    grype --config "$ANCHORE_CONFIG_PATH" --output json "$ANCHORE_IMAGE" > "$ANCHORE_JSON" 2>/dev/null || {
      echo "[run_anchore.sh][Anchore] Scan failed, continuing..." | tee -a "$LOG_FILE"
    }
    
    # Generate text output
    grype --config "$ANCHORE_CONFIG_PATH" "$ANCHORE_IMAGE" > "$ANCHORE_TEXT" 2>/dev/null || {
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

