#!/bin/bash
# Individual Kube-hunter Scan Script for SimpleSecCheck

# Expected Environment Variables:
# KUBE_HUNTER_CONFIG_PATH: Path to Kube-hunter configuration file
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
KUBE_HUNTER_CONFIG_PATH="${KUBE_HUNTER_CONFIG_PATH:-/SimpleSecCheck/kube-hunter/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_kube_hunter.sh] Initializing Kube-hunter scan..." | tee -a "$LOG_FILE"

if command -v kube-hunter &>/dev/null; then
  echo "[run_kube_hunter.sh][Kube-hunter] Running Kubernetes cluster security scan..." | tee -a "$LOG_FILE"
  
  KUBE_HUNTER_JSON="$RESULTS_DIR/kube-hunter.json"
  KUBE_HUNTER_TEXT="$RESULTS_DIR/kube-hunter.txt"
  
  # Run Kube-hunter scan with JSON output (with timeout to avoid hanging)
  echo "[run_kube_hunter.sh][Kube-hunter] Running cluster security scan..." | tee -a "$LOG_FILE"
  
  # Run with --remote flag to avoid interactive prompt, scan localhost with timeout
  timeout 10 kube-hunter --remote localhost --report json 2>/dev/null > "$KUBE_HUNTER_JSON" || {
    echo "[run_kube_hunter.sh][Kube-hunter] JSON report generation failed or timed out." >> "$LOG_FILE"
  }
  
  # Generate text report (with timeout)
  echo "[run_kube_hunter.sh][Kube-hunter] Running text report generation..." | tee -a "$LOG_FILE"
  timeout 10 kube-hunter --remote localhost --report plain 2>/dev/null > "$KUBE_HUNTER_TEXT" || {
    echo "[run_kube_hunter.sh][Kube-hunter] Text report generation failed or timed out." >> "$LOG_FILE"
  }
  
  if [ -f "$KUBE_HUNTER_JSON" ] || [ -f "$KUBE_HUNTER_TEXT" ]; then
    echo "[run_kube_hunter.sh][Kube-hunter] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$KUBE_HUNTER_JSON" ] && echo "  - $KUBE_HUNTER_JSON" | tee -a "$LOG_FILE"
    [ -f "$KUBE_HUNTER_TEXT" ] && echo "  - $KUBE_HUNTER_TEXT" | tee -a "$LOG_FILE"
    echo "[Kube-hunter] Kubernetes cluster security scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_kube_hunter.sh][Kube-hunter][ERROR] No Kube-hunter report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_kube_hunter.sh][ERROR] kube-hunter not found, skipping Kubernetes security scan." | tee -a "$LOG_FILE"
  exit 1
fi

