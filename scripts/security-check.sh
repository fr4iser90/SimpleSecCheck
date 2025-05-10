#!/bin/bash
# SecuLite Security Check Script
# Usage:
#   ZAP_TARGET="http://dein-ziel:port" HTML_REPORT=1 ./scripts/security-check.sh
#   oder
#   ./scripts/security-check.sh [ZAP_TARGET_URL]
# Default: http://localhost:8000
set -euo pipefail

# === DEBUG: Print environment and ZAP script status ===
echo "[DEBUG] PATH: $PATH"
echo "[DEBUG] ls -l /usr/local/bin/"
ls -l /usr/local/bin/
echo "[DEBUG] ls -l /opt/ZAP_2.16.1/"
ls -l /opt/ZAP_2.16.1/ || echo "/opt/ZAP_2.16.1/ not found"
echo "[DEBUG] command -v zap-baseline.py: $(command -v zap-baseline.py || echo not found)"

# Check for python3 availability (required for ZAP)
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 is not installed or not in PATH. ZAP scan cannot run. Please install python3." | tee -a "$LOG_FILE"
  exit 1
fi

# Ziel-URL für ZAP bestimmen
ZAP_TARGET="${ZAP_TARGET:-${1:-http://localhost:8000}}"
HTML_REPORT="${HTML_REPORT:-0}"

# Usage: ./scripts/security-check.sh [TARGET_PATH]
TARGET_PATH="${1:-..}"
RESULTS_DIR="/seculite/results"
LOG_FILE="/seculite/logs/security-check.log"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"
SUMMARY_JSON="$RESULTS_DIR/security-summary.json"

mkdir -p "$RESULTS_DIR" "/seculite/logs"

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
  export ZAP_PATH=/opt/ZAP_2.16.1
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
  echo "[ZAP] ENV: ZAP_PATH=$ZAP_PATH JAVA_HOME=$JAVA_HOME" | tee -a "$LOG_FILE"
  echo "[ZAP] Running baseline scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  ZAP_TMP_REPORT="/tmp/zap-report.xml"
  python3 /usr/local/bin/zap-baseline.py -d -t "$ZAP_TARGET" -r "$ZAP_TMP_REPORT" 2>>"$LOG_FILE" || {
    echo "[ZAP] Scan failed" >> "$LOG_FILE"
    if [[ "$ZAP_TARGET" =~ localhost ]]; then
      echo "[ZAP] ERROR: Das Ziel $ZAP_TARGET ist aus dem Container nicht erreichbar!" | tee -a "$LOG_FILE"
      echo "[ZAP] Lösung: Setze ZAP_TARGET=\"http://host.docker.internal:8000\" und stelle sicher, dass dein Webserver auf 0.0.0.0 lauscht." | tee -a "$LOG_FILE"
    fi
  }
  if [ -f "$ZAP_TMP_REPORT" ]; then
    cp "$ZAP_TMP_REPORT" "$RESULTS_DIR/zap-report.xml"
  else
    echo "[ZAP] ERROR: Report wurde nicht erzeugt! Pfad: $ZAP_TMP_REPORT" | tee -a "$LOG_FILE"
    exit 2
  fi
  if [ "$HTML_REPORT" = "1" ]; then
    ZAP_TMP_HTML="/tmp/zap-report.html"
    python3 /usr/local/bin/zap-baseline.py -d -t "$ZAP_TARGET" -f html -o "$ZAP_TMP_HTML" 2>>"$LOG_FILE" || echo "[ZAP] HTML report failed" >> "$LOG_FILE"
    if [ -f "$ZAP_TMP_HTML" ]; then
      cp "$ZAP_TMP_HTML" "$RESULTS_DIR/zap-report.html"
    else
      echo "[ZAP] ERROR: HTML-Report wurde nicht erzeugt! Pfad: $ZAP_TMP_HTML" | tee -a "$LOG_FILE"
      exit 2
    fi
  fi
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
  if [ "$HTML_REPORT" = "1" ]; then
    trivy fs --config trivy/config.yaml "$TARGET_PATH" --format template --template "@/usr/local/share/trivy/templates/html.tpl" > "$RESULTS_DIR/trivy.html" 2>>"$LOG_FILE" || echo "[Trivy] HTML report failed" >> "$LOG_FILE"
  fi
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

exit 0 