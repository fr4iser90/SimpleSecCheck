#!/bin/bash
# SecuLite Security Check Script
# Usage:
#   ZAP_TARGET="http://dein-ziel:port" HTML_REPORT=1 ./scripts/security-check.sh
#   oder
#   ./scripts/security-check.sh [ZAP_TARGET_URL]
# Default: http://localhost:8000

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
  # Do not exit, continue
fi

# Ziel-URL für ZAP bestimmen
ZAP_TARGET="${ZAP_TARGET:-${1:-http://localhost:8000}}"
HTML_REPORT="${HTML_REPORT:-0}"

# Usage: ./scripts/security-check.sh [TARGET_PATH]
# Set scan target to /seculite (project root inside container)
TARGET_PATH="/seculite"
RESULTS_DIR="/seculite/results"
LOGS_DIR="/seculite/logs"
LOG_FILE="$LOGS_DIR/security-check.log"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"
SUMMARY_JSON="$RESULTS_DIR/security-summary.json"

mkdir -p "$RESULTS_DIR" "$LOGS_DIR"
echo "[DEBUG] Listing $RESULTS_DIR before ZAP scan:"
ls -l "$RESULTS_DIR"

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
  # Do not exit, continue
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
    # Do not exit, continue
  fi
fi

echo "[DEBUG] Testing write permissions in $RESULTS_DIR"
touch "$RESULTS_DIR/test-write.txt" && echo "[DEBUG] Write test succeeded" || echo "[DEBUG] Write test FAILED"
rm -f "$RESULTS_DIR/test-write.txt"

# Run ZAP Baseline Scan
if command -v zap-baseline.py &>/dev/null; then
  export ZAP_PATH=/opt/ZAP_2.16.1
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
  echo "[ZAP] ENV: ZAP_PATH=$ZAP_PATH JAVA_HOME=$JAVA_HOME" | tee -a "$LOG_FILE"
  echo "[ZAP] Running baseline scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  ZAP_REPORT_XML="$RESULTS_DIR/zap-report.xml"
  ZAP_REPORT_HTML="$RESULTS_DIR/zap-report.html"
  ZAP_REPORT_XMLHTML="$RESULTS_DIR/zap-report.xml.html"
  REL_ZAP_REPORT_XML="zap-report.xml"
  REL_ZAP_REPORT_HTML="zap-report.html"
  echo "[DEBUG] Running ZAP with absolute path: $ZAP_REPORT_XML"
  python3 /usr/local/bin/zap-baseline.py -d -t "$ZAP_TARGET" -x "$ZAP_REPORT_XML" 2>>"$LOG_FILE" || {
    echo "[ZAP] Scan failed (absolute path)" >> "$LOG_FILE"
  }
  # Fallback: search for zap-report.xml anywhere and copy to results if missing
  if [ ! -f "$ZAP_REPORT_XML" ]; then
    FOUND_XML=$(find / -type f -name 'zap-report.xml' 2>/dev/null | head -n 1)
    if [ -n "$FOUND_XML" ]; then
      cp "$FOUND_XML" "$ZAP_REPORT_XML"
      echo "[DEBUG] Copied fallback zap-report.xml from $FOUND_XML to $ZAP_REPORT_XML" >> "$LOG_FILE"
    else
      echo "[DEBUG] No zap-report.xml found anywhere in container." >> "$LOG_FILE"
    fi
  fi
  echo "[DEBUG] Running ZAP with relative path: $REL_ZAP_REPORT_XML"
  python3 /usr/local/bin/zap-baseline.py -d -t "$ZAP_TARGET" -r "$REL_ZAP_REPORT_XML" 2>>"$LOG_FILE" || {
    echo "[ZAP] Scan failed (relative path)" >> "$LOG_FILE"
  }
  python3 /usr/local/bin/zap-baseline.py -d -t "$ZAP_TARGET" -f html -o "$ZAP_REPORT_HTML" 2>>"$LOG_FILE" || echo "[ZAP] HTML report failed" >> "$LOG_FILE"
  echo "[DEBUG] Listing $RESULTS_DIR after ZAP scan:"
  ls -l "$RESULTS_DIR"
  echo "[DEBUG] Searching for any zap-report* files and copying to $RESULTS_DIR"
  find / -type f -name 'zap-report*' -exec cp --no-clobber {} "$RESULTS_DIR" \; 2>/dev/null
  ls -l "$RESULTS_DIR"
  if [ -f "$ZAP_REPORT_XML" ] || [ -f "$ZAP_REPORT_HTML" ] || [ -f "$ZAP_REPORT_XMLHTML" ]; then
    echo "[ZAP] Report(s) erfolgreich erzeugt:"
    [ -f "$ZAP_REPORT_XML" ] && echo "  - $ZAP_REPORT_XML"
    [ -f "$ZAP_REPORT_HTML" ] && echo "  - $ZAP_REPORT_HTML"
    [ -f "$ZAP_REPORT_XMLHTML" ] && echo "  - $ZAP_REPORT_XMLHTML"
  else
    echo "[ZAP] ERROR: Kein Report wurde erzeugt!" | tee -a "$LOG_FILE"
    # Do not exit, continue
  fi
  echo "[ZAP] Baseline scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[ZAP] zap-baseline.py not found, skipping ZAP scan." | tee -a "$LOG_FILE"
fi

# Run Semgrep
if command -v semgrep &>/dev/null; then
  echo "[Semgrep] Running code scan..." | tee -a "$LOG_FILE"
  semgrep --config /seculite/rules "$TARGET_PATH" --json > "$RESULTS_DIR/semgrep.json" 2>>"$LOG_FILE" || echo "[Semgrep] Scan failed" >> "$LOG_FILE"
  semgrep --config /seculite/rules "$TARGET_PATH" --text > "$RESULTS_DIR/semgrep.txt" 2>>"$LOG_FILE"
  echo "[Semgrep] Code scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[Semgrep] semgrep not found, skipping code scan." | tee -a "$LOG_FILE"
fi

# Run Trivy
if command -v trivy &>/dev/null; then
  echo "[Trivy] Running dependency/container scan..." | tee -a "$LOG_FILE"
  trivy fs --config /seculite/trivy/config.yaml "$TARGET_PATH" --format json > "$RESULTS_DIR/trivy.json" 2>>"$LOG_FILE" || echo "[Trivy] Scan failed" >> "$LOG_FILE"
  trivy fs --config /seculite/trivy/config.yaml "$TARGET_PATH" --format table > "$RESULTS_DIR/trivy.txt" 2>>"$LOG_FILE"
  if [ "$HTML_REPORT" = "1" ]; then
    trivy fs --config /seculite/trivy/config.yaml "$TARGET_PATH" --format template --template "@/usr/local/share/trivy/templates/html.tpl" > "$RESULTS_DIR/trivy.html" 2>>"$LOG_FILE" || echo "[Trivy] HTML report failed" >> "$LOG_FILE"
  fi
  echo "[Trivy] Dependency/container scan complete." | tee -a "$SUMMARY_TXT"
else
  echo "[Trivy] trivy not found, skipping dependency/container scan." | tee -a "$LOG_FILE"
fi

# Aggregate Results
{
  echo "==== ZAP Report (XML) ===="
  [ -f "$RESULTS_DIR/zap-report.xml" ] && cat "$RESULTS_DIR/zap-report.xml" || echo "No ZAP XML report."
  echo
  echo "==== ZAP Report (HTML) ===="
  [ -f "$RESULTS_DIR/zap-report.html" ] && cat "$RESULTS_DIR/zap-report.html" || echo "No ZAP HTML report."
  echo
  echo "==== ZAP Report (XMLHTML) ===="
  [ -f "$RESULTS_DIR/zap-report.xml.html" ] && cat "$RESULTS_DIR/zap-report.xml.html" || echo "No ZAP XMLHTML report."
  echo
  echo "==== Semgrep Findings ===="
  [ -f "$RESULTS_DIR/semgrep.txt" ] && cat "$RESULTS_DIR/semgrep.txt" || echo "No Semgrep findings."
  echo
  echo "==== Trivy Findings ===="
  [ -f "$RESULTS_DIR/trivy.txt" ] && cat "$RESULTS_DIR/trivy.txt" || echo "No Trivy findings."
} > "$SUMMARY_TXT"

jq -s 'reduce .[] as $item ({}; . * $item)' "$RESULTS_DIR/semgrep.json" "$RESULTS_DIR/trivy.json" 2>/dev/null > "$SUMMARY_JSON" || echo '{"error": "Could not aggregate JSON results"}' > "$SUMMARY_JSON"

# Always generate the unified HTML report inside the container
python3 /seculite/scripts/generate-html-report.py

echo "[SecuLite] Security checks complete. See $SUMMARY_TXT, $SUMMARY_JSON, and security-summary.html for results." | tee -a "$LOG_FILE" 

exit 0 