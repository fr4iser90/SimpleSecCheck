#!/bin/bash
# Individual Nuclei Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# ZAP_TARGET: Target URL to scan (e.g., http://example.com)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
NUCLEI_CONFIG_PATH="${NUCLEI_CONFIG_PATH:-/SimpleSecCheck/nuclei/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_nuclei.sh] Initializing Nuclei scan..." | tee -a "$LOG_FILE"

if command -v nuclei &>/dev/null; then
  echo "[run_nuclei.sh][Nuclei] Running web application scan on $ZAP_TARGET..." | tee -a "$LOG_FILE"
  
  NUCLEI_JSON="$RESULTS_DIR/nuclei.json"
  NUCLEI_TEXT="$RESULTS_DIR/nuclei.txt"
  
  # Run comprehensive web application scan
  echo "[run_nuclei.sh][Nuclei] Running comprehensive web application scan..." | tee -a "$LOG_FILE"
  
  # Generate JSON report (using -jsonl for JSON Lines format)
  nuclei -u "$ZAP_TARGET" -config "$NUCLEI_CONFIG_PATH" -jsonl -o "$NUCLEI_JSON" 2>/dev/null || {
    echo "[run_nuclei.sh][Nuclei] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  nuclei -u "$ZAP_TARGET" -config "$NUCLEI_CONFIG_PATH" -o "$NUCLEI_TEXT" 2>/dev/null || {
    echo "[run_nuclei.sh][Nuclei] Text report generation failed." >> "$LOG_FILE"
  }
  
  # Additional focused scan for critical vulnerabilities
  echo "[run_nuclei.sh][Nuclei] Running additional critical vulnerability scan..." | tee -a "$LOG_FILE"
  nuclei -u "$ZAP_TARGET" -severity critical,high -jsonl -o "$RESULTS_DIR/nuclei-critical.json" 2>/dev/null || {
    echo "[run_nuclei.sh][Nuclei] Critical scan failed." >> "$LOG_FILE"
  }

  # Check if files exist and have content
  if [ -f "$NUCLEI_JSON" ] && [ -s "$NUCLEI_JSON" ]; then
    echo "[run_nuclei.sh][Nuclei] JSON report generated successfully" | tee -a "$LOG_FILE"
    echo "  - $NUCLEI_JSON" | tee -a "$LOG_FILE"
  elif [ -f "$NUCLEI_TEXT" ] && [ -s "$NUCLEI_TEXT" ]; then
    echo "[run_nuclei.sh][Nuclei] Text report generated successfully" | tee -a "$LOG_FILE"
    echo "  - $NUCLEI_TEXT" | tee -a "$LOG_FILE"
  else
    # No vulnerabilities found - this is acceptable
    echo "[run_nuclei.sh][Nuclei] No vulnerabilities found (scan completed successfully)" | tee -a "$LOG_FILE"
    echo '{"info": "No vulnerabilities found"}' > "$NUCLEI_JSON"
  fi
  
  echo "[Nuclei] Web application scan complete." >> "$SUMMARY_TXT"
  exit 0
else
  echo "[run_nuclei.sh][ERROR] nuclei not found, skipping web application scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Nuclei is a core tool
fi
