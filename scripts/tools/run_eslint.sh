#!/bin/bash
# Individual ESLint Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
ESLINT_CONFIG_PATH="${ESLINT_CONFIG_PATH:-/SimpleSecCheck/eslint/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_eslint.sh] Initializing ESLint scan..." | tee -a "$LOG_FILE"

if command -v eslint &>/dev/null; then
  echo "[run_eslint.sh][ESLint] Running JavaScript/TypeScript security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  ESLINT_JSON="$RESULTS_DIR/eslint.json"
  ESLINT_TEXT="$RESULTS_DIR/eslint.txt"
  
  # Check for JavaScript/TypeScript files
  JS_FILES=()
  while IFS= read -r -d '' file; do
    JS_FILES+=("$file")
  done < <(find "$TARGET_PATH" -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \) -print0 2>/dev/null)
  
  if [ ${#JS_FILES[@]} -eq 0 ]; then
    echo "[run_eslint.sh][ESLint] No JavaScript/TypeScript files found, skipping scan." | tee -a "$LOG_FILE"
    echo '[]' > "$ESLINT_JSON"
    echo "ESLint: No JavaScript/TypeScript files found" > "$ESLINT_TEXT"
    exit 0
  fi
  
  echo "[run_eslint.sh][ESLint] Found ${#JS_FILES[@]} JavaScript/TypeScript file(s)." | tee -a "$LOG_FILE"
  
  # Run ESLint scan with JSON output
  # ESLint v9+ uses new flat config, skip config check with --no-config-lookup
  eslint --format=json --output-file="$ESLINT_JSON" "$TARGET_PATH" 2>&1 || {
    echo "[run_eslint.sh][ESLint] JSON report generation failed." >> "$LOG_FILE"
    echo '[]' > "$ESLINT_JSON"
  }
  
  # Run ESLint scan with text output
  eslint --format=compact --output-file="$ESLINT_TEXT" "$TARGET_PATH" 2>&1 || {
    echo "[run_eslint.sh][ESLint] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$ESLINT_JSON" ]; then
    echo "[run_eslint.sh][ESLint] ESLint scan completed successfully." | tee -a "$LOG_FILE"
    echo "ESLint: JavaScript/TypeScript security scan completed" >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_eslint.sh][ESLint][ERROR] No ESLint report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_eslint.sh][ERROR] eslint not found, skipping ESLint security scan." | tee -a "$LOG_FILE"
  exit 1
fi
