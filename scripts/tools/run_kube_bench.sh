#!/bin/bash
# Kube-bench Kubernetes Compliance Testing Script for SimpleSecCheck

# Expected Environment Variables:
# KUBE_BENCH_CONFIG_PATH: Path to Kube-bench configuration file
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
KUBE_BENCH_CONFIG_PATH="${KUBE_BENCH_CONFIG_PATH:-/SimpleSecCheck/kube-bench/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_kube_bench.sh] Initializing Kube-bench scan..." | tee -a "$LOG_FILE"


if command -v kube-bench &>/dev/null; then
  echo "[run_kube_bench.sh][Kube-bench] Running Kubernetes compliance scan..." | tee -a "$LOG_FILE"
  
  KUBE_BENCH_JSON="$RESULTS_DIR/kube-bench.json"
  KUBE_BENCH_TEXT="$RESULTS_DIR/kube-bench.txt"
  
  # Run Kube-bench scan with JSON output
  echo "[run_kube_bench.sh][Kube-bench] Running compliance scan..." | tee -a "$LOG_FILE"
  
  # Run kube-bench with JSON and text outputs
  kube-bench --json > "$KUBE_BENCH_JSON" 2>>"$LOG_FILE" || {
    echo "[run_kube_bench.sh][Kube-bench] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  echo "[run_kube_bench.sh][Kube-bench] Running text report generation..." | tee -a "$LOG_FILE"
  kube-bench --version 1.28 > "$KUBE_BENCH_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_kube_bench.sh][Kube-bench] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$KUBE_BENCH_JSON" ] || [ -f "$KUBE_BENCH_TEXT" ]; then
    echo "[run_kube_bench.sh][Kube-bench] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$KUBE_BENCH_JSON" ] && echo "  - $KUBE_BENCH_JSON" | tee -a "$LOG_FILE"
    [ -f "$KUBE_BENCH_TEXT" ] && echo "  - $KUBE_BENCH_TEXT" | tee -a "$LOG_FILE"
    echo "[Kube-bench] Kubernetes compliance scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_kube_bench.sh][Kube-bench][ERROR] No Kube-bench report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_kube_bench.sh][ERROR] kube-bench not found, skipping Kubernetes compliance scan." | tee -a "$LOG_FILE"
  exit 1
fi

