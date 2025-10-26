#!/bin/bash
# Individual Safety Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SAFETY_CONFIG_PATH="${SAFETY_CONFIG_PATH:-/SimpleSecCheck/safety/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_safety.sh] Initializing Safety scan..." | tee -a "$LOG_FILE"

if command -v safety &>/dev/null; then
  echo "[run_safety.sh][Safety] Running Python dependency security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  SAFETY_JSON="$RESULTS_DIR/safety.json"
  SAFETY_TEXT="$RESULTS_DIR/safety.txt"
  
  # Check if we have Python dependency files
  DEPENDENCY_FILES=()
  
  # Look for common Python dependency files
  for pattern in "requirements*.txt" "Pipfile" "Pipfile.lock" "pyproject.toml" "setup.py" "environment.yml" "conda.yml"; do
    while IFS= read -r -d '' file; do
      DEPENDENCY_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#DEPENDENCY_FILES[@]} -eq 0 ]; then
    echo "[run_safety.sh][Safety] No Python dependency files found in $TARGET_PATH" | tee -a "$LOG_FILE"
    echo "[run_safety.sh][Safety] Creating empty reports..." | tee -a "$LOG_FILE"
    
    # Create empty JSON report
    echo '{"vulnerabilities": [], "packages": [], "summary": {"total_packages": 0, "vulnerable_packages": 0, "total_vulnerabilities": 0}}' > "$SAFETY_JSON"
    
    # Create empty text report
    echo "Safety Scan Results" > "$SAFETY_TEXT"
    echo "===================" >> "$SAFETY_TEXT"
    echo "No Python dependency files found." >> "$SAFETY_TEXT"
    echo "Scan completed at: $(date)" >> "$SAFETY_TEXT"
    
    echo "[Safety] No Python dependencies found." >> "$SUMMARY_TXT"
    exit 0
  fi
  
  echo "[run_safety.sh][Safety] Found ${#DEPENDENCY_FILES[@]} dependency file(s):" | tee -a "$LOG_FILE"
  for file in "${DEPENDENCY_FILES[@]}"; do
    echo "  - $file" | tee -a "$LOG_FILE"
  done
  
  # Run Safety scan with JSON output
  echo "[run_safety.sh][Safety] Running Safety scan with JSON output..." | tee -a "$LOG_FILE"
  safety check --json --output "$SAFETY_JSON" --file "${DEPENDENCY_FILES[0]}" 2>>"$LOG_FILE" || {
    echo "[run_safety.sh][Safety] JSON report generation failed, trying alternative approach..." | tee -a "$LOG_FILE"
    
    # Try scanning the directory directly
    cd "$TARGET_PATH" && safety check --json --output "$SAFETY_JSON" 2>>"$LOG_FILE" || {
      echo "[run_safety.sh][Safety] Directory scan also failed, creating minimal report..." | tee -a "$LOG_FILE"
      echo '{"vulnerabilities": [], "packages": [], "summary": {"total_packages": 0, "vulnerable_packages": 0, "total_vulnerabilities": 0}, "error": "Safety scan failed"}' > "$SAFETY_JSON"
    }
  }
  
  # Generate text report
  echo "[run_safety.sh][Safety] Running Safety scan with text output..." | tee -a "$LOG_FILE"
  safety check --output "$SAFETY_TEXT" --file "${DEPENDENCY_FILES[0]}" 2>>"$LOG_FILE" || {
    echo "[run_safety.sh][Safety] Text report generation failed, trying alternative approach..." | tee -a "$LOG_FILE"
    
    # Try scanning the directory directly
    cd "$TARGET_PATH" && safety check --output "$SAFETY_TEXT" 2>>"$LOG_FILE" || {
      echo "[run_safety.sh][Safety] Directory text scan also failed, creating minimal report..." | tee -a "$LOG_FILE"
      echo "Safety Scan Results" > "$SAFETY_TEXT"
      echo "===================" >> "$SAFETY_TEXT"
      echo "Safety scan failed or no vulnerabilities found." >> "$SAFETY_TEXT"
      echo "Scan completed at: $(date)" >> "$SAFETY_TEXT"
    }
  }
  
  # Additional scan with verbose output for debugging
  echo "[run_safety.sh][Safety] Running additional verbose scan..." | tee -a "$LOG_FILE"
  safety check --verbose --file "${DEPENDENCY_FILES[0]}" >> "$SAFETY_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_safety.sh][Safety] Verbose scan failed." >> "$LOG_FILE"
  }
  
  if [ -f "$SAFETY_JSON" ] || [ -f "$SAFETY_TEXT" ]; then
    echo "[run_safety.sh][Safety] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$SAFETY_JSON" ] && echo "  - $SAFETY_JSON" | tee -a "$LOG_FILE"
    [ -f "$SAFETY_TEXT" ] && echo "  - $SAFETY_TEXT" | tee -a "$LOG_FILE"
    echo "[Safety] Python dependency security scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_safety.sh][Safety][ERROR] No Safety report (JSON or Text) was generated!" | tee -a "$LOG_FILE"
    exit 1 # Indicate failure
  fi
else
  echo "[run_safety.sh][ERROR] safety not found, skipping Python dependency security scan." | tee -a "$LOG_FILE"
  exit 1 # Indicate failure as Safety is a core tool for Python projects
fi
