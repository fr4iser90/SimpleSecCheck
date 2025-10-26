#!/bin/bash
# Individual OWASP Dependency Check Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to scan (e.g., /target for filesystem)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# OWASP_DC_CONFIG_PATH: Path to OWASP Dependency Check configuration file.
# OWASP_DC_DATA_DIR: Directory for OWASP Dependency Check data and cache.

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
OWASP_DC_CONFIG_PATH="${OWASP_DC_CONFIG_PATH:-/SimpleSecCheck/owasp-dependency-check/config.yaml}"
OWASP_DC_DATA_DIR="${OWASP_DC_DATA_DIR:-/SimpleSecCheck/owasp-dependency-check-data}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")" "$OWASP_DC_DATA_DIR"

# Initialize OWASP Dependency Check database if not present
initialize_db() {
  LOCK_FILE="$OWASP_DC_DATA_DIR/odc.update.lock"
  
  # Check if lock file exists and remove it automatically (likely from interrupted update)
  if [ -f "$LOCK_FILE" ]; then
    echo "[run_owasp_dependency_check.sh] Lock file found from previous session, removing..." | tee -a "$LOG_FILE"
    rm -f "$LOCK_FILE"
  fi
  
  if [ ! -d "$OWASP_DC_DATA_DIR" ] || [ -z "$(ls -A "$OWASP_DC_DATA_DIR" 2>/dev/null)" ]; then
    echo "[run_owasp_dependency_check.sh] OWASP Dependency Check database not found. Downloading vulnerability database (this may take 5-15 minutes)..." | tee -a "$LOG_FILE"
    if command -v dependency-check &>/dev/null; then
      NVD_FLAG=""
      if [ -n "$NVD_API_KEY" ]; then
        NVD_FLAG="--nvdApiKey=$NVD_API_KEY"
      fi
      dependency-check --updateonly --data "$OWASP_DC_DATA_DIR" $NVD_FLAG >> "$LOG_FILE" 2>&1 || {
        echo "[run_owasp_dependency_check.sh] Database download failed or incomplete, continuing with partial database..." | tee -a "$LOG_FILE"
      }
    else
      echo "[run_owasp_dependency_check.sh][ERROR] dependency-check command not found!" | tee -a "$LOG_FILE"
      exit 1
    fi
  else
    echo "[run_owasp_dependency_check.sh] Using existing OWASP Dependency Check database." | tee -a "$LOG_FILE"
  fi
}

echo "[run_owasp_dependency_check.sh] Initializing OWASP Dependency Check scan..." | tee -a "$LOG_FILE"

# Ensure database is initialized before scanning
initialize_db

if command -v dependency-check &>/dev/null; then
  echo "[run_owasp_dependency_check.sh][OWASP DC] Running dependency vulnerability scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  OWASP_DC_JSON="$RESULTS_DIR/owasp-dependency-check.json"
  OWASP_DC_HTML="$RESULTS_DIR/owasp-dependency-check.html"
  OWASP_DC_XML="$RESULTS_DIR/owasp-dependency-check.xml"
  
  # Create temporary directory for scan results
  TEMP_SCAN_DIR="/tmp/owasp-dc-scan-$$"
  mkdir -p "$TEMP_SCAN_DIR"
  
  # Check if NVD_API_KEY is provided
  NVD_FLAG=""
  if [ -n "$NVD_API_KEY" ]; then
    echo "[run_owasp_dependency_check.sh][OWASP DC] Using provided NVD_API_KEY for enhanced vulnerability data..." | tee -a "$LOG_FILE"
    NVD_FLAG="--nvdApiKey=$NVD_API_KEY"
  else
    echo "[run_owasp_dependency_check.sh][OWASP DC] No NVD_API_KEY provided, using public data rate limit..." | tee -a "$LOG_FILE"
  fi
  
  # Run OWASP Dependency Check with comprehensive scanning
  echo "[run_owasp_dependency_check.sh][OWASP DC] Running comprehensive dependency vulnerability scan..." | tee -a "$LOG_FILE"
  
  dependency-check \
    --project "SimpleSecCheck-Dependency-Scan" \
    --scan "$TARGET_PATH" \
    --format "JSON" \
    --format "HTML" \
    --format "XML" \
    --out "$TEMP_SCAN_DIR" \
    --data "$OWASP_DC_DATA_DIR" \
    $NVD_FLAG \
    --noupdate \
    >/dev/null 2>&1 || {
    echo "[run_owasp_dependency_check.sh][OWASP DC] Scan completed with warnings (rate limits may apply)..." >> "$LOG_FILE"
  }
  
  # Copy results to results directory
  if [ -f "$TEMP_SCAN_DIR/dependency-check-report.json" ]; then
    cp "$TEMP_SCAN_DIR/dependency-check-report.json" "$OWASP_DC_JSON"
    echo "[run_owasp_dependency_check.sh][OWASP DC] JSON report copied to $OWASP_DC_JSON" | tee -a "$LOG_FILE"
  fi
  
  if [ -f "$TEMP_SCAN_DIR/dependency-check-report.html" ]; then
    cp "$TEMP_SCAN_DIR/dependency-check-report.html" "$OWASP_DC_HTML"
    echo "[run_owasp_dependency_check.sh][OWASP DC] HTML report copied to $OWASP_DC_HTML" | tee -a "$LOG_FILE"
  fi
  
  if [ -f "$TEMP_SCAN_DIR/dependency-check-report.xml" ]; then
    cp "$TEMP_SCAN_DIR/dependency-check-report.xml" "$OWASP_DC_XML"
    echo "[run_owasp_dependency_check.sh][OWASP DC] XML report copied to $OWASP_DC_XML" | tee -a "$LOG_FILE"
  fi
  
  # Clean up temporary directory
  rm -rf "$TEMP_SCAN_DIR"
  
  # Check if any reports were generated
  if [ -f "$OWASP_DC_JSON" ] || [ -f "$OWASP_DC_HTML" ] || [ -f "$OWASP_DC_XML" ]; then
    echo "[run_owasp_dependency_check.sh][OWASP DC] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$OWASP_DC_JSON" ] && echo "  - $OWASP_DC_JSON" | tee -a "$LOG_FILE"
    [ -f "$OWASP_DC_HTML" ] && echo "  - $OWASP_DC_HTML" | tee -a "$LOG_FILE"
    [ -f "$OWASP_DC_XML" ] && echo "  - $OWASP_DC_XML" | tee -a "$LOG_FILE"
    echo "[OWASP Dependency Check] Dependency vulnerability scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_owasp_dependency_check.sh][OWASP DC][ERROR] No OWASP Dependency Check report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_owasp_dependency_check.sh][ERROR] dependency-check not found, skipping dependency vulnerability scan." | tee -a "$LOG_FILE"
  exit 1
fi
