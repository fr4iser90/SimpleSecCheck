#!/bin/bash
# SecuLite Security Check Script
# Make sure this script is executable: chmod +x scripts/security-check.sh
set -euo pipefail

# Usage: ./scripts/security-check.sh [TARGET_PATH]
TARGET_PATH="${1:-..}"
RESULTS_DIR="results"
LOG_FILE="logs/security-check.log"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"
SUMMARY_JSON="$RESULTS_DIR/security-summary.json"

mkdir -p "$RESULTS_DIR" "logs"

# Clear previous results
> "$SUMMARY_TXT"
> "$SUMMARY_JSON"
> "$LOG_FILE"

# Check for required tools
MISSING_TOOLS=()
for tool in semgrep trivy; do
  if ! command -v $tool &>/dev/null; then
    MISSING_TOOLS+=("$tool")
  fi
done
if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
  echo "[SecuLite] Missing required tools: ${MISSING_TOOLS[*]}" | tee -a "$LOG_FILE"
  echo "Please install all required tools before running the script." | tee -a "$LOG_FILE"
  exit 1
fi

# Ensure jq is installed
if ! command -v jq &>/dev/null; then
  echo "[SecuLite] jq not found, installing jq..." | tee -a "$LOG_FILE"
  if command -v apt-get &>/dev/null; then
    sudo apt-get update && sudo apt-get install -y jq
  elif command -v yum &>/dev/null; then
    sudo yum install -y jq
  else
    echo "[SecuLite] Please install jq manually." | tee -a "$LOG_FILE"
    exit 1
  fi
fi

# Run ZAP Baseline Scan
if command -v zap-baseline.py &>/dev/null; then
  echo "[ZAP] Running baseline scan..." | tee -a "$LOG_FILE"
  zap-baseline.py -t "http://localhost:8000" -c zap/baseline.conf -r "$RESULTS_DIR/zap-report.xml" 2>>"$LOG_FILE" || echo "[ZAP] Scan failed" >> "$LOG_FILE"
  echo "[ZAP] Baseline scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[ZAP] zap-baseline.py not found, skipping ZAP scan." | tee -a "$LOG_FILE"
fi

# Run Semgrep
if command -v semgrep &>/dev/null; then
  echo "[Semgrep] Running code scan..." | tee -a "$LOG_FILE"
  semgrep --config rules/ "$TARGET_PATH" --json > "$RESULTS_DIR/semgrep.json" 2>>"$LOG_FILE" || echo "[Semgrep] Scan failed" >> "$LOG_FILE"
  semgrep --config rules/ "$TARGET_PATH" --text > "$RESULTS_DIR/semgrep.txt" 2>>"$LOG_FILE"
  echo "[Semgrep] Code scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[Semgrep] semgrep not found, skipping code scan." | tee -a "$LOG_FILE"
fi

# Run Trivy
if command -v trivy &>/dev/null; then
  echo "[Trivy] Running dependency/container scan..." | tee -a "$LOG_FILE"
  trivy fs --config trivy/config.yaml "$TARGET_PATH" --format json > "$RESULTS_DIR/trivy.json" 2>>"$LOG_FILE" || echo "[Trivy] Scan failed" >> "$LOG_FILE"
  trivy fs --config trivy/config.yaml "$TARGET_PATH" --format table > "$RESULTS_DIR/trivy.txt" 2>>"$LOG_FILE"
  echo "[Trivy] Dependency/container scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[Trivy] trivy not found, skipping dependency/container scan." | tee -a "$LOG_FILE"
fi

# Aggregate Results
{
  echo "==== ZAP Report ===="
  [ -f "$RESULTS_DIR/zap-report.xml" ] && cat "$RESULTS_DIR/zap-report.xml" || echo "No ZAP report."
  echo
  echo "==== Semgrep Findings ===="
  [ -f "$RESULTS_DIR/semgrep.txt" ] && cat "$RESULTS_DIR/semgrep.txt" || echo "No Semgrep findings."
  echo
  echo "==== Trivy Findings ===="
  [ -f "$RESULTS_DIR/trivy.txt" ] && cat "$RESULTS_DIR/trivy.txt" || echo "No Trivy findings."
} > "$SUMMARY_TXT"

jq -s 'reduce .[] as $item ({}; . * $item)' "$RESULTS_DIR/semgrep.json" "$RESULTS_DIR/trivy.json" 2>/dev/null > "$SUMMARY_JSON" || echo '{"error": "Could not aggregate JSON results"}' > "$SUMMARY_JSON"

echo "[SecuLite] Security checks complete. See $SUMMARY_TXT and $SUMMARY_JSON for results." | tee -a "$LOG_FILE" 