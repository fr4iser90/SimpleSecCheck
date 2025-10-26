#!/bin/bash
# Individual Terraform Security Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
TERRAFORM_SECURITY_CONFIG_PATH="${TERRAFORM_SECURITY_CONFIG_PATH:-/SimpleSecCheck/terraform-security/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_terraform_security.sh] Initializing Terraform security scan..." | tee -a "$LOG_FILE"

if command -v checkov &>/dev/null; then
  echo "[run_terraform_security.sh][Checkov] Running Terraform security scan on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CHECKOV_JSON="$RESULTS_DIR/checkov.json"
  CHECKOV_TEXT="$RESULTS_DIR/checkov.txt"
  
  # Check for Terraform files
  TERRAFORM_FILES=()
  
  # Look for common Terraform files
  for pattern in "*.tf" "*.tfvars"; do
    while IFS= read -r -d '' file; do
      TERRAFORM_FILES+=("$file")
    done < <(find "$TARGET_PATH" -name "$pattern" -type f -print0 2>/dev/null)
  done
  
  if [ ${#TERRAFORM_FILES[@]} -eq 0 ]; then
    echo "[run_terraform_security.sh][Checkov] No Terraform files found, skipping scan." | tee -a "$LOG_FILE"
    exit 0
  fi
  
  echo "[run_terraform_security.sh][Checkov] Found ${#TERRAFORM_FILES[@]} Terraform file(s)." | tee -a "$LOG_FILE"
  
  # Generate JSON report
  checkov -d "$TARGET_PATH" --framework terraform --output json --output-file "$CHECKOV_JSON" 2>>"$LOG_FILE" || {
    echo "[run_terraform_security.sh][Checkov] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  checkov -d "$TARGET_PATH" --framework terraform --output cli --output-file "$CHECKOV_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_terraform_security.sh][Checkov] Text report generation failed." >> "$LOG_FILE"
  }
  
  if [ -f "$CHECKOV_JSON" ] || [ -f "$CHECKOV_TEXT" ]; then
    echo "[run_terraform_security.sh][Checkov] Scan completed successfully." | tee -a "$LOG_FILE"
    echo "[Checkov] Terraform security scan complete." >> "$SUMMARY_TXT"
  else
    echo "[run_terraform_security.sh][Checkov] No results generated." >> "$LOG_FILE"
  fi
else
  echo "[run_terraform_security.sh][Checkov] Checkov CLI not found, skipping scan." | tee -a "$LOG_FILE"
fi

