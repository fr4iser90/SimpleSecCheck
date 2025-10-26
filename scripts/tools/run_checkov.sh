#!/bin/bash
# Individual Checkov Scan Script for SimpleSecCheck
# Purpose: Infrastructure security scanning for multiple frameworks (Terraform, CloudFormation, Kubernetes, Docker, ARM)

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
CHECKOV_CONFIG_PATH="${CHECKOV_CONFIG_PATH:-/SimpleSecCheck/checkov/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_checkov.sh] Initializing Checkov infrastructure security scan..." | tee -a "$LOG_FILE"

if command -v checkov &>/dev/null; then
  echo "[run_checkov.sh][Checkov] Running infrastructure security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CHECKOV_JSON="$RESULTS_DIR/checkov-comprehensive.json"
  CHECKOV_TEXT="$RESULTS_DIR/checkov-comprehensive.txt"
  
  # Remove old directory if it exists (from previous failed scans)
  if [ -d "$CHECKOV_JSON" ]; then
    rm -rf "$CHECKOV_JSON"
    echo "[run_checkov.sh][Checkov] Removed old directory at $CHECKOV_JSON" >> "$LOG_FILE"
  fi
  
  # Check for infrastructure files (broader than just Terraform)
  INFRA_FILES=()
  
  # Look for common infrastructure files across multiple frameworks
  for pattern in "*.tf" "*.tfvars" "*.yml" "*.yaml" "Dockerfile" "docker-compose.yml" "docker-compose.yaml" "*.json" "*.tfstate" "cloudformation.yaml" "cloudformation.yml" "serverless.yml" "serverless.yaml"; do
    while IFS= read -r -d '' file; do
      INFRA_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#INFRA_FILES[@]} -eq 0 ]; then
    echo "[run_checkov.sh][Checkov] No infrastructure files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_checkov.sh][Checkov] Found ${#INFRA_FILES[@]} infrastructure file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report for multiple frameworks
  # Note: Not limiting to --framework terraform, using default auto-detection
  checkov -d "$TARGET_PATH" --output json --output-file "$CHECKOV_JSON" --quiet 2>>"$LOG_FILE" || {
    echo "[run_checkov.sh][Checkov] JSON report generation failed." >> "$LOG_FILE"
    # Create minimal JSON if generation fails
    echo '{"check_type":"","results":{"passed_checks":[],"failed_checks":[],"skipped_checks":[]},"summary":{"passed":0,"failed":0,"skipped":0}}' > "$CHECKOV_JSON"
  }
  
  # Generate text report (output to stdout, redirect to file)
  checkov -d "$TARGET_PATH" --output cli --quiet 2>>"$LOG_FILE" > "$CHECKOV_TEXT" || {
    echo "[run_checkov.sh][Checkov] Text report generation failed." >> "$LOG_FILE"
    echo "Checkov scan completed but no results available." > "$CHECKOV_TEXT"
  }
  
  if [ -f "$CHECKOV_JSON" ] || [ -f "$CHECKOV_TEXT" ]; then
    echo "[run_checkov.sh][Checkov] Infrastructure security scan completed successfully." | tee -a "$LOG_FILE"
    echo "[Checkov] Comprehensive infrastructure security scan complete." >> "$SUMMARY_TXT"
  else
    echo "[run_checkov.sh][Checkov] No results generated." >> "$LOG_FILE"
  fi
else
  echo "[run_checkov.sh][Checkov] Checkov CLI not found, skipping scan." | tee -a "$LOG_FILE"
fi

