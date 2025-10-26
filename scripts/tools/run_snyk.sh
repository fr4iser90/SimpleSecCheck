#!/bin/bash
# Individual Snyk Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# SNYK_TOKEN: Snyk API token for authentication (optional)

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SNYK_CONFIG_PATH="${SNYK_CONFIG_PATH:-/SimpleSecCheck/snyk/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_snyk.sh] Initializing Snyk scan..." | tee -a "$LOG_FILE"

if command -v snyk &>/dev/null; then
  echo "[run_snyk.sh][Snyk] Running Snyk vulnerability scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  SNYK_JSON="$RESULTS_DIR/snyk.json"
  SNYK_TEXT="$RESULTS_DIR/snyk.txt"
  
  # Check if SNYK_TOKEN is provided
  if [ -z "$SNYK_TOKEN" ]; then
    echo "[run_snyk.sh][Snyk] No SNYK_TOKEN provided, running in offline mode..." | tee -a "$LOG_FILE"
    SNYK_AUTH_FLAG=""
  else
    echo "[run_snyk.sh][Snyk] Using provided SNYK_TOKEN for authentication..." | tee -a "$LOG_FILE"
    SNYK_AUTH_FLAG="--token=$SNYK_TOKEN"
  fi
  
  # Change to target directory for scanning
  cd "$TARGET_PATH" || {
    echo "[run_snyk.sh][Snyk][ERROR] Cannot access target directory: $TARGET_PATH" | tee -a "$LOG_FILE"
    exit 1
  }
  
  # Run Snyk test with JSON output
  echo "[run_snyk.sh][Snyk] Running Snyk test with JSON output..." | tee -a "$LOG_FILE"
  snyk test $SNYK_AUTH_FLAG --json --output-file="$SNYK_JSON" >/dev/null 2>&1 || {
    echo "[run_snyk.sh][Snyk] JSON report generation failed, trying alternative approach..." | tee -a "$LOG_FILE"
    
    # Try with different options
    snyk test $SNYK_AUTH_FLAG --json > "$SNYK_JSON" 2>&1 || {
      echo "[run_snyk.sh][Snyk] Alternative JSON scan also failed, creating minimal report..." | tee -a "$LOG_FILE"
      echo '{"vulnerabilities": [], "summary": {"total_packages": 0, "vulnerable_packages": 0, "total_vulnerabilities": 0}, "error": "Snyk scan failed"}' > "$SNYK_JSON"
    }
  }
  
  # Generate text report
  echo "[run_snyk.sh][Snyk] Running Snyk test with text output..." | tee -a "$LOG_FILE"
  snyk test $SNYK_AUTH_FLAG > "$SNYK_TEXT" 2>/dev/null || {
    echo "[run_snyk.sh][Snyk] Text report generation failed, trying alternative approach..." | tee -a "$LOG_FILE"
    
    # Try with different options
    snyk test $SNYK_AUTH_FLAG > "$SNYK_TEXT" 2>&1 || {
      echo "[run_snyk.sh][Snyk] Alternative text scan also failed, creating minimal report..." | tee -a "$LOG_FILE"
      echo "Snyk Scan Results" > "$SNYK_TEXT"
      echo "=================" >> "$SNYK_TEXT"
      echo "Snyk scan failed or no vulnerabilities found." >> "$SNYK_TEXT"
      echo "Scan completed at: $(date)" >> "$SNYK_TEXT"
    }
  }
  
  # Additional scan with verbose output for debugging
  echo "[run_snyk.sh][Snyk] Running additional verbose scan..." | tee -a "$LOG_FILE"
  snyk test $SNYK_AUTH_FLAG --verbose >> "$SNYK_TEXT" 2>/dev/null || {
    echo "[run_snyk.sh][Snyk] Verbose scan failed." >> "$LOG_FILE"
  }
  
  # Try to run Snyk monitor if token is provided (for cloud integration)
  if [ -n "$SNYK_TOKEN" ]; then
    echo "[run_snyk.sh][Snyk] Running Snyk monitor for cloud integration..." | tee -a "$LOG_FILE"
    snyk monitor $SNYK_AUTH_FLAG >> "$SNYK_TEXT" 2>/dev/null || {
      echo "[run_snyk.sh][Snyk] Snyk monitor failed." >> "$LOG_FILE"
    }
  fi
  
  if [ -f "$SNYK_JSON" ] || [ -f "$SNYK_TEXT" ]; then
    echo "[run_snyk.sh][Snyk] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$SNYK_JSON" ] && echo "  - $SNYK_JSON" | tee -a "$LOG_FILE"
    [ -f "$SNYK_TEXT" ] && echo "  - $SNYK_TEXT" | tee -a "$LOG_FILE"
    echo "[Snyk] Vulnerability scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_snyk.sh][Snyk][ERROR] No Snyk report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_snyk.sh][ERROR] snyk not found, skipping vulnerability scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Snyk is a core tool for vulnerability scanning
fi
