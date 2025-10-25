#!/bin/bash
# SimpleSecCheck - Main Security Check Orchestrator (NEW)
# Purpose: Coordinates various security scanning tools and generates a consolidated report,
# using the user-provided tool scripts.

# Ensure script exits on any error
set -e

# === Configuration ===
# Script's own directory to reliably find other scripts
ORCHESTRATOR_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_SCRIPTS_DIR="$ORCHESTRATOR_SCRIPT_DIR/tools"

# --- Define Core Paths (these are absolute paths INSIDE the container) ---
# These align with Dockerfile COPY commands and docker-compose.yml volume mounts.
export BASE_PROJECT_DIR="/SimpleSecCheck" # Base directory where all project files are copied in Docker
export TARGET_PATH_IN_CONTAINER="/target" # Where host code is mounted for scanning
export RESULTS_DIR_IN_CONTAINER="$BASE_PROJECT_DIR/results"
export LOGS_DIR_IN_CONTAINER="$BASE_PROJECT_DIR/logs"
export LOG_FILE="$LOGS_DIR_IN_CONTAINER/security-check.log" # Central log file

# --- Tool Specific Configurations (absolute paths INSIDE container) ---
export SEMGREP_RULES_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/rules"
export TRIVY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/trivy/config.yaml"
export ZAP_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/zap/baseline.conf" # Note: your run_zap.sh hardcodes this.

# ZAP_TARGET is passed from run-docker.sh
export ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"

# --- Determine scan type ---
export SCAN_TYPE="${SCAN_TYPE:-code}" # Default to code scan

# --- Other Environment Variables for Tool Scripts ---
export TRIVY_SCAN_TYPE="${TRIVY_SCAN_TYPE:-fs}" # Default scan type for Trivy

# --- Script Control & Setup ---
LOCK_FILE="$RESULTS_DIR_IN_CONTAINER/.scan-running"

# === Script Functions ===
log_message() {
    # Appends to the central log file
    echo "[SimpleSecCheck Orchestrator] ($(date '+%Y-%m-%d %H:%M:%S')) ($BASHPID) $1" | tee -a "$LOG_FILE"
}

cleanup_lock() {
    if [ -f "$LOCK_FILE" ]; then
        log_message "Removing lock file: $LOCK_FILE"
        rm -f "$LOCK_FILE"
    fi
}
trap cleanup_lock EXIT SIGINT SIGTERM

# === Main Execution Start ===
mkdir -p "$RESULTS_DIR_IN_CONTAINER" "$LOGS_DIR_IN_CONTAINER"

# Initialize log file for this run
# Note: Your tool scripts also use `tee -a "$LOG_FILE"` so they will append.
echo "----- SimpleSecCheck Scan Run Initialized: $(date '+%Y-%m-%d %H:%M:%S') -----" > "$LOG_FILE"
log_message "Orchestrator script started."
log_message "Scan Type: $SCAN_TYPE"
log_message "Container Base Project Dir (BASE_PROJECT_DIR): $BASE_PROJECT_DIR"
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "Host Code Mount for Scanning (TARGET_PATH_IN_CONTAINER): $TARGET_PATH_IN_CONTAINER"
fi
log_message "Results Directory (RESULTS_DIR_IN_CONTAINER): $RESULTS_DIR_IN_CONTAINER"
log_message "Logs Directory (LOGS_DIR_IN_CONTAINER): $LOGS_DIR_IN_CONTAINER"
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "Semgrep Rules Path (SEMGREP_RULES_PATH_IN_CONTAINER): $SEMGREP_RULES_PATH_IN_CONTAINER"
    log_message "Trivy Config Path (TRIVY_CONFIG_PATH_IN_CONTAINER): $TRIVY_CONFIG_PATH_IN_CONTAINER"
fi
if [ "$SCAN_TYPE" = "website" ]; then
    log_message "ZAP DAST Target (ZAP_TARGET): $ZAP_TARGET"
fi

# Lock File Management
if [ -f "$LOCK_FILE" ]; then
    log_message "[ERROR] Lock file $LOCK_FILE exists. Another scan may be in progress or failed to clean up. Exiting."
    exit 1
fi
log_message "Creating lock file: $LOCK_FILE"
touch "$LOCK_FILE"

OVERALL_SUCCESS=true

# --- Execute Tool Scripts ---

# Only run code analysis tools for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_semgrep.sh before calling it
    log_message "--- Orchestrating Semgrep Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is already exported and used by run_semgrep.sh's `tee -a`
    export SEMGREP_RULES_PATH="$SEMGREP_RULES_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_semgrep.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_semgrep.sh..."
        # Output of run_semgrep.sh (which uses `tee -a "$LOG_FILE"`) will go to the log.
        # We also capture its stdout/stderr here for additional orchestrator logging if needed, though it might be redundant.
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_semgrep.sh"; then
            log_message "run_semgrep.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_semgrep.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_semgrep.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Semgrep Scan Orchestration Finished ---"
else
    log_message "--- Skipping Semgrep Scan (Website scan mode) ---"
fi

# Only run Trivy for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_trivy.sh
    log_message "--- Orchestrating Trivy Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER" # Re-export for clarity, though it's the same
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export TRIVY_CONFIG_PATH="$TRIVY_CONFIG_PATH_IN_CONTAINER"
    # TRIVY_SCAN_TYPE is exported
    if [ -f "$TOOL_SCRIPTS_DIR/run_trivy.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_trivy.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_trivy.sh"; then
            log_message "run_trivy.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_trivy.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_trivy.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Trivy Scan Orchestration Finished ---"
else
    log_message "--- Skipping Trivy Scan (Website scan mode) ---"
fi

# Only run ZAP for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_zap.sh
    log_message "--- Orchestrating ZAP Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    # ZAP_CONFIG_PATH_IN_CONTAINER is available if run_zap.sh decides to use it via an env var instead of hardcoding.
    # Your current run_zap.sh hardcodes /SimpleSecCheck/zap/baseline.conf, which matches ZAP_CONFIG_PATH_IN_CONTAINER.
    if [ -f "$TOOL_SCRIPTS_DIR/run_zap.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_zap.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_zap.sh"; then
            log_message "run_zap.sh completed successfully (exit code 0)."
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_zap.sh failed with exit code $EXIT_CODE."
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_zap.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- ZAP Scan Orchestration Finished ---"
else
    log_message "--- Skipping ZAP Scan (Code scan mode) ---"
fi

# --- Reporting Phase ---
HTML_REPORT_PY_SCRIPT="$ORCHESTRATOR_SCRIPT_DIR/generate-html-report.py"
HTML_REPORT_OUTPUT_FILE="$RESULTS_DIR_IN_CONTAINER/security-summary.html"

# generate-html-report.py expects RESULTS_DIR and ZAP_TARGET as env vars.
# RESULTS_DIR is already exported as RESULTS_DIR_IN_CONTAINER.
# ZAP_TARGET is already exported.
# It also uses FP_WHITELIST_FILE if set.
export FP_WHITELIST_FILE="${FP_WHITELIST_FILE:-$BASE_PROJECT_DIR/conf/fp_whitelist.json}" # Default if not set

log_message "Checking for HTML report generator: $HTML_REPORT_PY_SCRIPT"
if [ -f "$HTML_REPORT_PY_SCRIPT" ]; then
    log_message "Generating consolidated HTML report to $HTML_REPORT_OUTPUT_FILE..."
    # The generate-html-report.py script's debug messages will go to stderr, which is not captured by default here.
    # To capture its stderr into the main log, you'd add 2>&1 after it.
    if PYTHONUNBUFFERED=1 python3 "$HTML_REPORT_PY_SCRIPT" >> "$LOG_FILE" 2>&1; then
        log_message "HTML report generation script completed successfully."
    else
        EXIT_CODE=$?
        log_message "[ORCHESTRATOR ERROR] HTML report generation script ($HTML_REPORT_PY_SCRIPT) failed with exit code $EXIT_CODE."
        OVERALL_SUCCESS=false
    fi
else
    log_message "[ORCHESTRATOR ERROR] HTML report script $HTML_REPORT_PY_SCRIPT not found!"
    OVERALL_SUCCESS=false
fi

# Copy webui.js (if it exists in the orchestrator's script directory)
WEBUI_JS_SOURCE="$ORCHESTRATOR_SCRIPT_DIR/webui.js"
WEBUI_JS_DEST="$RESULTS_DIR_IN_CONTAINER/webui.js"
if [ -f "$WEBUI_JS_SOURCE" ]; then
    cp "$WEBUI_JS_SOURCE" "$WEBUI_JS_DEST"
    log_message "webui.js copied to $WEBUI_JS_DEST"
else
    log_message "[WARN] webui.js not found at $WEBUI_JS_SOURCE, not copied."
fi

log_message "SimpleSecCheck Security Scan Sequence Completed."
if [ "$OVERALL_SUCCESS" = true ]; then
    log_message "All tool scripts and reporting completed successfully."
    exit 0
else
    log_message "[FINAL STATUS: FAILED] One or more steps failed. Please review $LOG_FILE."
    exit 1
fi 