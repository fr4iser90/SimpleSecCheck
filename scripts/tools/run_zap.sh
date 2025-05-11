#!/bin/bash
# Individual ZAP Scan Script for SecuLite Plugin System

# Expected Environment Variables or Arguments:
# ZAP_TARGET: Target URL for ZAP (e.g., http://localhost:8000)
# RESULTS_DIR: Directory to store results (e.g., /seculite/results)
# LOG_FILE: Path to the main log file (e.g., /seculite/logs/security-check.log)

ZAP_TARGET="${ZAP_TARGET:-${1:-http://localhost:8000}}"
RESULTS_DIR="${RESULTS_DIR:-/seculite/results}"
LOG_FILE="${LOG_FILE:-/seculite/logs/security-check.log}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt" # For appending completion status

# Ensure results and logs directories exist (though main script should handle this)
mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_zap.sh] Initializing ZAP scan..." | tee -a "$LOG_FILE"

# Check for python3 availability (required for ZAP baseline script)
if ! command -v python3 &>/dev/null; then
  echo "[run_zap.sh][ERROR] python3 is not installed or not in PATH. ZAP scan cannot run." | tee -a "$LOG_FILE"
  exit 1
fi

if command -v zap-baseline.py &>/dev/null; then
  export ZAP_PATH=${ZAP_PATH:-/opt/ZAP_2.16.1} # Use existing ZAP_PATH or default
  export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64} # Use existing JAVA_HOME or default
  
  echo "[run_zap.sh][ZAP] ENV: ZAP_PATH=$ZAP_PATH JAVA_HOME=$JAVA_HOME" | tee -a "$LOG_FILE"
  echo "[run_zap.sh][ZAP] Running baseline scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  
  ZAP_REPORT_XML="$RESULTS_DIR/zap-report.xml"
  ZAP_REPORT_HTML="$RESULTS_DIR/zap-report.html"
  # ZAP_REPORT_XMLHTML="$RESULTS_DIR/zap-report.xml.html" # This format seems to be a duplicate sometimes or specific config
  
  echo "[run_zap.sh][DEBUG] Running ZAP to generate XML report: $ZAP_REPORT_XML"
  python3 /usr/local/bin/zap-baseline.py -c /seculite/zap/baseline.conf -t "$ZAP_TARGET" -x "$ZAP_REPORT_XML" -d 2>>"$LOG_FILE" || {
    echo "[run_zap.sh][ZAP] XML Report generation failed." >> "$LOG_FILE"
    # Try to find if a report was generated elsewhere (common in some ZAP setups)
    FALLBACK_XML=$(find / -type f -name 'zap-report.xml' 2>/dev/null | head -n 1)
    if [ -n "$FALLBACK_XML" ] && [ "$FALLBACK_XML" != "$ZAP_REPORT_XML" ]; then
      cp "$FALLBACK_XML" "$ZAP_REPORT_XML"
      echo "[run_zap.sh][DEBUG] Copied fallback zap-report.xml from $FALLBACK_XML to $ZAP_REPORT_XML" >> "$LOG_FILE"
    else
      echo "[run_zap.sh][DEBUG] No fallback zap-report.xml found." >> "$LOG_FILE"
    fi
  }

  echo "[run_zap.sh][DEBUG] Running ZAP to generate HTML report: $ZAP_REPORT_HTML"
  python3 /usr/local/bin/zap-baseline.py -c /seculite/zap/baseline.conf -t "$ZAP_TARGET" -r "zap-report.html" -d 2>>"$LOG_FILE" || {
    echo "[run_zap.sh][ZAP] HTML Report generation failed (using -r zap-report.html). Attempting with -o option." >> "$LOG_FILE"
    # Fallback to -o if -r fails, ensuring it is placed in RESULTS_DIR
    python3 /usr/local/bin/zap-baseline.py -c /seculite/zap/baseline.conf -t "$ZAP_TARGET" -f html -o "$ZAP_REPORT_HTML" -d 2>>"$LOG_FILE" || echo "[run_zap.sh][ZAP] HTML report generation failed with -o as well." >> "$LOG_FILE"
  }
  # Ensure HTML report is in the correct directory if -r was used
  if [ -f "zap-report.html" ] && [ ! -f "$ZAP_REPORT_HTML" ]; then
      mv "zap-report.html" "$ZAP_REPORT_HTML"
      echo "[run_zap.sh][DEBUG] Moved zap-report.html to $ZAP_REPORT_HTML" | tee -a "$LOG_FILE"
  fi

  echo "[run_zap.sh][DEBUG] Listing $RESULTS_DIR after ZAP scan attempt:" | tee -a "$LOG_FILE"
  ls -l "$RESULTS_DIR" | tee -a "$LOG_FILE"
  
  # Check if at least one report was generated
  if [ -f "$ZAP_REPORT_XML" ] || [ -f "$ZAP_REPORT_HTML" ]; then
    echo "[run_zap.sh][ZAP] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$ZAP_REPORT_XML" ] && echo "  - $ZAP_REPORT_XML" | tee -a "$LOG_FILE"
    [ -f "$ZAP_REPORT_HTML" ] && echo "  - $ZAP_REPORT_HTML" | tee -a "$LOG_FILE"
    echo "[ZAP] Baseline scan complete." >> "$SUMMARY_TXT" # Append to main summary
    exit 0
  else
    echo "[run_zap.sh][ZAP][ERROR] No ZAP report (XML or HTML) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_zap.sh][ERROR] zap-baseline.py not found, skipping ZAP scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as ZAP is a core tool
fi 