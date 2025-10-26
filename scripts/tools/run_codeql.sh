#!/bin/bash
# Individual CodeQL Scan Script for SimpleSecCheck Plugin System

# Expected Environment Variables or Arguments:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# CODEQL_CONFIG_PATH: Path to CodeQL configuration file
# CODEQL_QUERIES_PATH: Path to CodeQL queries directory

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
CODEQL_CONFIG_PATH="${CODEQL_CONFIG_PATH:-/SimpleSecCheck/codeql/config.yaml}"
CODEQL_QUERIES_PATH="${CODEQL_QUERIES_PATH:-/SimpleSecCheck/codeql/queries}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_codeql.sh] Initializing CodeQL scan..." | tee -a "$LOG_FILE"

if command -v codeql &>/dev/null; then
  echo "[run_codeql.sh][CodeQL] Running code analysis on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CODEQL_JSON="$RESULTS_DIR/codeql.json"
  CODEQL_SARIF="$RESULTS_DIR/codeql.sarif"
  CODEQL_TEXT="$RESULTS_DIR/codeql.txt"
  CODEQL_DB_DIR="$RESULTS_DIR/codeql-database"
  
  # Detect programming languages in the target
  echo "[run_codeql.sh][CodeQL] Detecting programming languages..." | tee -a "$LOG_FILE"
  DETECTED_LANGUAGES=$(codeql resolve languages --format=json "$TARGET_PATH" 2>/dev/null | jq -r '.[]' 2>/dev/null || echo "")
  
  if [ -z "$DETECTED_LANGUAGES" ]; then
    echo "[run_codeql.sh][CodeQL] Auto-detection failed, trying common languages..." | tee -a "$LOG_FILE"
    # Try common languages if auto-detection fails
    if find "$TARGET_PATH" -name "*.py" -o -name "*.js" -o -name "*.java" -o -name "*.cpp" -o -name "*.c" -o -name "*.cs" -o -name "*.go" | head -1 | grep -q .; then
      if find "$TARGET_PATH" -name "*.py" | head -1 | grep -q .; then DETECTED_LANGUAGES="python"; fi
      if find "$TARGET_PATH" -name "*.js" -o -name "*.ts" | head -1 | grep -q .; then DETECTED_LANGUAGES="$DETECTED_LANGUAGES javascript"; fi
      if find "$TARGET_PATH" -name "*.java" | head -1 | grep -q .; then DETECTED_LANGUAGES="$DETECTED_LANGUAGES java"; fi
      if find "$TARGET_PATH" -name "*.cpp" -o -name "*.c" -o -name "*.h" | head -1 | grep -q .; then DETECTED_LANGUAGES="$DETECTED_LANGUAGES cpp"; fi
      if find "$TARGET_PATH" -name "*.cs" | head -1 | grep -q .; then DETECTED_LANGUAGES="$DETECTED_LANGUAGES csharp"; fi
      if find "$TARGET_PATH" -name "*.go" | head -1 | grep -q .; then DETECTED_LANGUAGES="$DETECTED_LANGUAGES go"; fi
    fi
  fi
  
  if [ -z "$DETECTED_LANGUAGES" ]; then
    echo "[run_codeql.sh][CodeQL][WARNING] No supported languages detected, skipping CodeQL scan." | tee -a "$LOG_FILE"
    echo "[CodeQL] No supported languages found, scan skipped." >> "$SUMMARY_TXT"
    exit 0
  fi
  
  echo "[run_codeql.sh][CodeQL] Detected languages: $DETECTED_LANGUAGES" | tee -a "$LOG_FILE"
  
  # Create CodeQL database
  echo "[run_codeql.sh][CodeQL] Creating CodeQL database..." | tee -a "$LOG_FILE"
  for lang in $DETECTED_LANGUAGES; do
    echo "[run_codeql.sh][CodeQL] Creating database for language: $lang" | tee -a "$LOG_FILE"
    
    # For C++ in Docker single-shot, skip if we detect npm install issues
    if [ "$lang" = "cpp" ]; then
      # Check if there are C++ files that aren't Node.js related
      CPP_COUNT=$(find "$TARGET_PATH" \( -name "*.cpp" -o -name "*.c" -o -name "*.h" -o -name "*.hpp" \) ! -path "*/node_modules/*" | wc -l)
      if [ "$CPP_COUNT" -eq 0 ]; then
        echo "[run_codeql.sh][CodeQL] No C++ source files found (only node_modules), skipping C++ database creation" | tee -a "$LOG_FILE"
        continue
      fi
    fi
    
    # Disable autobuilder for C++ in Docker to avoid npm install issues with read-only filesystem
    if [ "$lang" = "cpp" ]; then
      echo "[run_codeql.sh][CodeQL] Creating C++ database without autobuilder (to avoid read-only filesystem issues)..." | tee -a "$LOG_FILE"
      codeql database create "$CODEQL_DB_DIR-$lang" --language="$lang" --source-root="$TARGET_PATH" --command="" --threads=4 2>>"$LOG_FILE" || {
        echo "[run_codeql.sh][CodeQL] Database creation failed for $lang" | tee -a "$LOG_FILE"
        continue
      }
    else
      codeql database create "$CODEQL_DB_DIR-$lang" --language="$lang" --source-root="$TARGET_PATH" --threads=4 2>>"$LOG_FILE" || {
        echo "[run_codeql.sh][CodeQL] Database creation failed for $lang" | tee -a "$LOG_FILE"
        continue
      }
    fi
    
    # Run security and quality queries
    echo "[run_codeql.sh][CodeQL] Running security and quality queries for $lang..." | tee -a "$LOG_FILE"
    
    # Run security queries
    codeql database analyze "$CODEQL_DB_DIR-$lang" \
      --format=sarif-latest \
      --output="$CODEQL_SARIF-$lang" \
      --threads=4 \
      --timeout=600 \
      "$lang-security-and-quality.qls" 2>>"$LOG_FILE" || {
      echo "[run_codeql.sh][CodeQL] Security queries failed for $lang" | tee -a "$LOG_FILE"
    }
    
    # Convert SARIF to JSON for processing
    if [ -f "$CODEQL_SARIF-$lang" ]; then
      echo "[run_codeql.sh][CodeQL] Converting SARIF to JSON for $lang..." | tee -a "$LOG_FILE"
      codeql bqrs decode "$CODEQL_SARIF-$lang" --format=json --output="$CODEQL_JSON-$lang" 2>>"$LOG_FILE" || {
        echo "[run_codeql.sh][CodeQL] SARIF to JSON conversion failed for $lang" | tee -a "$LOG_FILE"
      }
    fi
    
    # Generate text report
    echo "[run_codeql.sh][CodeQL] Generating text report for $lang..." | tee -a "$LOG_FILE"
    codeql database analyze "$CODEQL_DB_DIR-$lang" \
      --format=text \
      --output="$CODEQL_TEXT-$lang" \
      --threads=4 \
      --timeout=600 \
      "$lang-security-and-quality.qls" 2>>"$LOG_FILE" || {
      echo "[run_codeql.sh][CodeQL] Text report generation failed for $lang" | tee -a "$LOG_FILE"
    }
  done
  
  # Combine all language results into single files
  echo "[run_codeql.sh][CodeQL] Combining results from all languages..." | tee -a "$LOG_FILE"
  
  # Combine JSON results
  COMBINED_JSON="$RESULTS_DIR/codeql-combined.json"
  echo '{"runs":[]}' > "$COMBINED_JSON"
  for lang in $DETECTED_LANGUAGES; do
    if [ -f "$CODEQL_JSON-$lang" ]; then
      echo "[run_codeQL.sh][CodeQL] Adding $lang results to combined JSON..." | tee -a "$LOG_FILE"
      # Simple combination - in production, you'd want proper JSON merging
      cat "$CODEQL_JSON-$lang" >> "$COMBINED_JSON" 2>/dev/null || true
    fi
  done
  
  # Combine SARIF results
  COMBINED_SARIF="$RESULTS_DIR/codeql-combined.sarif"
  echo '{"$schema":"https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json","version":"2.1.0","runs":[]}' > "$COMBINED_SARIF"
  for lang in $DETECTED_LANGUAGES; do
    if [ -f "$CODEQL_SARIF-$lang" ]; then
      echo "[run_codeql.sh][CodeQL] Adding $lang SARIF results..." | tee -a "$LOG_FILE"
      # Simple combination - in production, you'd want proper SARIF merging
      cat "$CODEQL_SARIF-$lang" >> "$COMBINED_SARIF" 2>/dev/null || true
    fi
  done
  
  # Combine text results
  COMBINED_TEXT="$RESULTS_DIR/codeql-combined.txt"
  echo "CodeQL Analysis Results" > "$COMBINED_TEXT"
  echo "=======================" >> "$COMBINED_TEXT"
  for lang in $DETECTED_LANGUAGES; do
    if [ -f "$CODEQL_TEXT-$lang" ]; then
      echo "" >> "$COMBINED_TEXT"
      echo "=== $lang Results ===" >> "$COMBINED_TEXT"
      cat "$CODEQL_TEXT-$lang" >> "$COMBINED_TEXT"
    fi
  done
  
  # Create final output files
  if [ -f "$COMBINED_JSON" ] && [ -s "$COMBINED_JSON" ]; then
    cp "$COMBINED_JSON" "$CODEQL_JSON"
    echo "[run_codeql.sh][CodeQL] Combined JSON report: $CODEQL_JSON" | tee -a "$LOG_FILE"
  fi
  
  if [ -f "$COMBINED_SARIF" ] && [ -s "$COMBINED_SARIF" ]; then
    cp "$COMBINED_SARIF" "$CODEQL_SARIF"
    echo "[run_codeql.sh][CodeQL] Combined SARIF report: $CODEQL_SARIF" | tee -a "$LOG_FILE"
  fi
  
  if [ -f "$COMBINED_TEXT" ] && [ -s "$COMBINED_TEXT" ]; then
    cp "$COMBINED_TEXT" "$CODEQL_TEXT"
    echo "[run_codeql.sh][CodeQL] Combined text report: $CODEQL_TEXT" | tee -a "$LOG_FILE"
  fi
  
  # Clean up individual language files
  echo "[run_codeql.sh][CodeQL] Cleaning up temporary files..." | tee -a "$LOG_FILE"
  rm -f "$CODEQL_JSON"-* "$CODEQL_SARIF"-* "$CODEQL_TEXT"-* "$COMBINED_JSON" "$COMBINED_SARIF" "$COMBINED_TEXT"
  rm -rf "$CODEQL_DB_DIR"-*
  
  if [ -f "$CODEQL_JSON" ] || [ -f "$CODEQL_SARIF" ] || [ -f "$CODEQL_TEXT" ]; then
    echo "[run_codeql.sh][CodeQL] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$CODEQL_JSON" ] && echo "  - $CODEQL_JSON" | tee -a "$LOG_FILE"
    [ -f "$CODEQL_SARIF" ] && echo "  - $CODEQL_SARIF" | tee -a "$LOG_FILE"
    [ -f "$CODEQL_TEXT" ] && echo "  - $CODEQL_TEXT" | tee -a "$LOG_FILE"
    echo "[CodeQL] Code analysis complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_codeql.sh][CodeQL][ERROR] No CodeQL report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_codeql.sh][ERROR] codeql not found, skipping code analysis." | tee -a "$LOG_FILE"
  exit 1
fi
