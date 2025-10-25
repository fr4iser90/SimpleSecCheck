#!/bin/bash
# Individual Semgrep Scan Script for SecuLite Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /seculite/results)
# LOG_FILE: Path to the main log file (e.g., /seculite/logs/security-check.log)

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/seculite/results}"
LOG_FILE="${LOG_FILE:-/seculite/logs/security-check.log}"
SEMGREP_RULES_PATH="${SEMGREP_RULES_PATH:-/seculite/rules}" # Default rules path
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_semgrep.sh] Initializing Semgrep scan..." | tee -a "$LOG_FILE"

if command -v semgrep &>/dev/null; then
  echo "[run_semgrep.sh][Semgrep] Running code scan on $TARGET_PATH using rules from $SEMGREP_RULES_PATH..." | tee -a "$LOG_FILE"
  
  SEMOLINA_JSON="$RESULTS_DIR/semgrep.json"
  SEMOLINA_TEXT="$RESULTS_DIR/semgrep.txt"
  
  # Deep analysis with multiple rule sets and aggressive scanning
  echo "[run_semgrep.sh][Semgrep] Running DEEP analysis with multiple rule sets..." | tee -a "$LOG_FILE"
  
  # Run with custom rules + auto rules for comprehensive coverage
  semgrep --config "$SEMGREP_RULES_PATH" --config auto "$TARGET_PATH" --json -o "$SEMOLINA_JSON" --severity=ERROR --severity=WARNING --severity=INFO 2>>"$LOG_FILE" || {
    echo "[run_semgrep.sh][Semgrep] JSON report generation failed." >> "$LOG_FILE"
    # Still try to generate text report
  }
  
  # Generate detailed text report with verbose output
  semgrep --config "$SEMGREP_RULES_PATH" --config auto "$TARGET_PATH" --text -o "$SEMOLINA_TEXT" --severity=ERROR --severity=WARNING --severity=INFO --verbose 2>>"$LOG_FILE" || {
    echo "[run_semgrep.sh][Semgrep] Text report generation failed." >> "$LOG_FILE"
  }
  
  # Additional deep scan with specific security-focused rules
  echo "[run_semgrep.sh][Semgrep] Running additional security-focused deep scan..." | tee -a "$LOG_FILE"
  semgrep --config "p/security-audit" --config "p/secrets" --config "p/owasp-top-ten" "$TARGET_PATH" --json -o "$RESULTS_DIR/semgrep-security-deep.json" 2>>"$LOG_FILE" || {
    echo "[run_semgrep.sh][Semgrep] Security deep scan failed." >> "$LOG_FILE"
  }
  
  if [ -f "$SEMOLINA_JSON" ] || [ -f "$SEMOLINA_TEXT" ]; then
    echo "[run_semgrep.sh][Semgrep] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$SEMOLINA_JSON" ] && echo "  - $SEMOLINA_JSON" | tee -a "$LOG_FILE"
    [ -f "$SEMOLINA_TEXT" ] && echo "  - $SEMOLINA_TEXT" | tee -a "$LOG_FILE"
    echo "[Semgrep] Code scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_semgrep.sh][Semgrep][ERROR] No Semgrep report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_semgrep.sh][ERROR] semgrep not found, skipping code scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Semgrep is a core tool
fi 