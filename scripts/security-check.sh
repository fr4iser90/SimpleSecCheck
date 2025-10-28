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
# RESULTS_DIR_IN_CONTAINER and LOGS_DIR_IN_CONTAINER will be set based on PROJECT_RESULTS_DIR or derived below
export RESULTS_DIR_IN_CONTAINER="${PROJECT_RESULTS_DIR:-$BASE_PROJECT_DIR/results}"
export LOGS_DIR_IN_CONTAINER="${PROJECT_LOGS_DIR:-$BASE_PROJECT_DIR/logs}"
export LOG_FILE="$LOGS_DIR_IN_CONTAINER/security-check.log" # Central log file

# --- Tool Specific Configurations (absolute paths INSIDE container) ---
export SEMGREP_RULES_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/rules"
export TRIVY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/trivy/config.yaml"
export CODEQL_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/codeql/config.yaml"
export CODEQL_QUERIES_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/codeql/queries"
export OWASP_DC_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/owasp-dependency-check/config.yaml"
export OWASP_DC_DATA_DIR_IN_CONTAINER="$BASE_PROJECT_DIR/owasp-dependency-check-data"
export SAFETY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/safety/config.yaml"
export SNYK_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/snyk/config.yaml"
export SONARQUBE_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/sonarqube/config.yaml"
export TERRAFORM_SECURITY_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/terraform-security/config.yaml"
export CHECKOV_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/checkov/config.yaml"
export TRUFFLEHOG_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/trufflehog/config.yaml"
export GITLEAKS_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/gitleaks/config.yaml"
export DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/detect-secrets/config.yaml"
export NPM_AUDIT_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/npm-audit/config.yaml"
export ZAP_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/zap/baseline.conf" # Note: your run_zap.sh hardcodes this.
export WAPITI_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/wapiti/config.yaml"
export KUBE_HUNTER_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/kube-hunter/config.yaml"
export KUBE_BENCH_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/kube-bench/config.yaml"
export DOCKER_BENCH_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/docker-bench/config.yaml"
export ESLINT_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/eslint/config.yaml"
export CLAIR_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/clair/config.yaml"
export ANCHORE_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/anchore/config.yaml"
export BURP_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/burp/config.yaml"
export BRAKEMAN_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/brakeman/config.yaml"
export BANDIT_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/bandit/config.yaml"
export CLAIR_IMAGE="${CLAIR_IMAGE:-}"
export ANCHORE_IMAGE="${ANCHORE_IMAGE:-}"

# ZAP_TARGET is passed from run-docker.sh
export ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"

# --- Determine scan type ---
export SCAN_TYPE="${SCAN_TYPE:-code}" # Default to code scan

# --- Other Environment Variables for Tool Scripts ---
export TRIVY_SCAN_TYPE="${TRIVY_SCAN_TYPE:-fs}" # Default scan type for Trivy

# --- Script Control & Setup ---
# LOCK_FILE will be set based on RESULTS_DIR_IN_CONTAINER below

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
# Check if we need to create a timestamp subdirectory (when running via direct docker run)
if [ -z "${PROJECT_RESULTS_DIR:-}" ]; then
    # Running directly via docker run, create timestamp subdirectory
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    if [ -n "${PROJECT_NAME:-}" ]; then
        # PROJECT_NAME explicitly provided
        SCAN_DIR="${PROJECT_NAME}_${TIMESTAMP}"
    elif [ "$SCAN_TYPE" = "code" ]; then
        # Try to get project name from /proc/self/mountinfo (Docker mount)
        if [ -f /proc/self/mountinfo ]; then
            # Format: mount_id parent_id major:minor root mount_point options - filesystem_type mount_source
            # Example: 2119 2110 259:2 /home/user/project /target ro,relatime - ext4 /dev/...
            # root (field 4) contains the host path!
            MOUNT_LINE=$(grep " $TARGET_PATH_IN_CONTAINER " /proc/self/mountinfo 2>/dev/null | tail -1)
            if [ -n "$MOUNT_LINE" ]; then
                # Extract field 4 (root directory - the host path)
                HOST_PATH=$(echo "$MOUNT_LINE" | awk '{print $4}')
                if [ -n "$HOST_PATH" ] && [ "$HOST_PATH" != "/" ]; then
                    # Clean up escaped spaces and get basename
                    HOST_PATH=$(echo "$HOST_PATH" | sed 's/\\040/ /g')
                    PROJECT_NAME=$(basename "$HOST_PATH" 2>/dev/null || echo "target")
                else
                    PROJECT_NAME="target"
                fi
            else
                PROJECT_NAME="target"
            fi
        else
            PROJECT_NAME="target"
        fi
        SCAN_DIR="${PROJECT_NAME}_${TIMESTAMP}"
    elif [ "$SCAN_TYPE" = "network" ]; then
        # Network scan - use network-infrastructure as project name
        SCAN_DIR="network-infrastructure_${TIMESTAMP}"
    elif [ "$SCAN_TYPE" = "website" ]; then
        # Website scan - use domain name from ZAP_TARGET
        if [ -n "${ZAP_TARGET:-}" ]; then
            # Extract domain from URL (e.g., http://example.com/path -> example.com)
            DOMAIN=$(echo "$ZAP_TARGET" | sed -e 's|http://||' -e 's|https://||' -e 's|/.*$||' -e 's|:.*$||')
            if [ -n "$DOMAIN" ]; then
                SCAN_DIR="${DOMAIN}_${TIMESTAMP}"
            else
                SCAN_DIR="website_${TIMESTAMP}"
            fi
        else
            SCAN_DIR="website_${TIMESTAMP}"
        fi
    else
        SCAN_DIR="scan_${TIMESTAMP}"
    fi
    RESULTS_DIR_IN_CONTAINER="$BASE_PROJECT_DIR/results/$SCAN_DIR"
    LOGS_DIR_IN_CONTAINER="$BASE_PROJECT_DIR/results/$SCAN_DIR/logs"
    LOG_FILE="$LOGS_DIR_IN_CONTAINER/security-check.log"
    LOCK_FILE="$RESULTS_DIR_IN_CONTAINER/.scan-running"
fi

# Set LOCK_FILE if not already set (when PROJECT_RESULTS_DIR was provided)
LOCK_FILE="${LOCK_FILE:-$RESULTS_DIR_IN_CONTAINER/.scan-running}"

# Fix ownership on mounted volumes to allow scanner user to write
sudo chown -R scanner:scanner "$RESULTS_DIR_IN_CONTAINER" "$LOGS_DIR_IN_CONTAINER" 2>/dev/null || true
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
    log_message "CodeQL Config Path (CODEQL_CONFIG_PATH_IN_CONTAINER): $CODEQL_CONFIG_PATH_IN_CONTAINER"
    log_message "CodeQL Queries Path (CODEQL_QUERIES_PATH_IN_CONTAINER): $CODEQL_QUERIES_PATH_IN_CONTAINER"
    log_message "OWASP Dependency Check Config Path (OWASP_DC_CONFIG_PATH_IN_CONTAINER): $OWASP_DC_CONFIG_PATH_IN_CONTAINER"
    log_message "OWASP Dependency Check Data Dir (OWASP_DC_DATA_DIR_IN_CONTAINER): $OWASP_DC_DATA_DIR_IN_CONTAINER"
    log_message "Safety Config Path (SAFETY_CONFIG_PATH_IN_CONTAINER): $SAFETY_CONFIG_PATH_IN_CONTAINER"
    log_message "Snyk Config Path (SNYK_CONFIG_PATH_IN_CONTAINER): $SNYK_CONFIG_PATH_IN_CONTAINER"
    log_message "SonarQube Config Path (SONARQUBE_CONFIG_PATH_IN_CONTAINER): $SONARQUBE_CONFIG_PATH_IN_CONTAINER"
    log_message "Checkov Config Path (CHECKOV_CONFIG_PATH_IN_CONTAINER): $CHECKOV_CONFIG_PATH_IN_CONTAINER"
    log_message "TruffleHog Config Path (TRUFFLEHOG_CONFIG_PATH_IN_CONTAINER): $TRUFFLEHOG_CONFIG_PATH_IN_CONTAINER"
    log_message "GitLeaks Config Path (GITLEAKS_CONFIG_PATH_IN_CONTAINER): $GITLEAKS_CONFIG_PATH_IN_CONTAINER"
    log_message "Detect-secrets Config Path (DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER): $DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER"
fi
if [ "$SCAN_TYPE" = "website" ]; then
    log_message "ZAP DAST Target (ZAP_TARGET): $ZAP_TARGET"
fi
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "Kube-hunter Config Path (KUBE_HUNTER_CONFIG_PATH_IN_CONTAINER): $KUBE_HUNTER_CONFIG_PATH_IN_CONTAINER"
    log_message "Kube-bench Config Path (KUBE_BENCH_CONFIG_PATH_IN_CONTAINER): $KUBE_BENCH_CONFIG_PATH_IN_CONTAINER"
    log_message "Docker Bench Config Path (DOCKER_BENCH_CONFIG_PATH_IN_CONTAINER): $DOCKER_BENCH_CONFIG_PATH_IN_CONTAINER"
    log_message "Clair Config Path (CLAIR_CONFIG_PATH_IN_CONTAINER): $CLAIR_CONFIG_PATH_IN_CONTAINER"
    log_message "Clair Image to Scan (CLAIR_IMAGE): $CLAIR_IMAGE"
    log_message "Anchore Config Path (ANCHORE_CONFIG_PATH_IN_CONTAINER): $ANCHORE_CONFIG_PATH_IN_CONTAINER"
    log_message "Anchore Image to Scan (ANCHORE_IMAGE): $ANCHORE_IMAGE"
    log_message "Brakeman Config Path (BRAKEMAN_CONFIG_PATH_IN_CONTAINER): $BRAKEMAN_CONFIG_PATH_IN_CONTAINER"
    log_message "Bandit Config Path (BANDIT_CONFIG_PATH_IN_CONTAINER): $BANDIT_CONFIG_PATH_IN_CONTAINER"
fi

# Lock File Management
if [ -f "$LOCK_FILE" ]; then
    log_message "[ERROR] Lock file $LOCK_FILE exists. Another scan may be in progress or failed to clean up. Exiting."
    exit 1
fi
log_message "Creating lock file: $LOCK_FILE"
touch "$LOCK_FILE"

OVERALL_SUCCESS=true

# Scanner tracking
declare -A SCANNER_STATUS
SCANNER_STATUS["Semgrep"]="SKIPPED"
SCANNER_STATUS["Trivy"]="SKIPPED"
SCANNER_STATUS["CodeQL"]="SKIPPED"
SCANNER_STATUS["OWASP_DC"]="SKIPPED"
SCANNER_STATUS["Safety"]="SKIPPED"
SCANNER_STATUS["Snyk"]="SKIPPED"
SCANNER_STATUS["SonarQube"]="SKIPPED"
SCANNER_STATUS["Checkov"]="SKIPPED"
SCANNER_STATUS["TruffleHog"]="SKIPPED"
SCANNER_STATUS["GitLeaks"]="SKIPPED"
SCANNER_STATUS["Detect-secrets"]="SKIPPED"
SCANNER_STATUS["npm_audit"]="SKIPPED"
SCANNER_STATUS["ESLint"]="SKIPPED"
SCANNER_STATUS["Brakeman"]="SKIPPED"
SCANNER_STATUS["Bandit"]="SKIPPED"
SCANNER_STATUS["Android"]="SKIPPED"
SCANNER_STATUS["iOS"]="SKIPPED"
SCANNER_STATUS["ZAP"]="SKIPPED"
SCANNER_STATUS["Nuclei"]="SKIPPED"
SCANNER_STATUS["Wapiti"]="SKIPPED"
SCANNER_STATUS["Nikto"]="SKIPPED"
SCANNER_STATUS["Burp"]="SKIPPED"
SCANNER_STATUS["Clair"]="SKIPPED"
SCANNER_STATUS["Anchore"]="SKIPPED"
SCANNER_STATUS["Terraform"]="SKIPPED"
SCANNER_STATUS["Kube-hunter"]="SKIPPED"
SCANNER_STATUS["Kube-bench"]="SKIPPED"
SCANNER_STATUS["Docker_bench"]="SKIPPED"

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
            SCANNER_STATUS["Semgrep"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_semgrep.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Semgrep"]="FAILED"
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
            SCANNER_STATUS["Trivy"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_trivy.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Trivy"]="FAILED"
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

# Only run Clair for code scans (if container image is specified)
if [ "$SCAN_TYPE" = "code" ] && [ -n "$CLAIR_IMAGE" ]; then
    log_message "--- Orchestrating Clair Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export CLAIR_CONFIG_PATH="$CLAIR_CONFIG_PATH_IN_CONTAINER"
    export CLAIR_IMAGE="$CLAIR_IMAGE"
    if [ -f "$TOOL_SCRIPTS_DIR/run_clair.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_clair.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_clair.sh"; then
            log_message "run_clair.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Clair"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_clair.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Clair"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_clair.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Clair Scan Orchestration Finished ---"
else
    if [ "$SCAN_TYPE" = "code" ]; then
        log_message "--- Skipping Clair Scan (no container image specified) ---"
    else
        log_message "--- Skipping Clair Scan (Website scan mode) ---"
    fi
fi

# Only run Anchore for code scans (if container image is specified)
if [ "$SCAN_TYPE" = "code" ] && [ -n "$ANCHORE_IMAGE" ]; then
    log_message "--- Orchestrating Anchore Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export ANCHORE_CONFIG_PATH="$ANCHORE_CONFIG_PATH_IN_CONTAINER"
    export ANCHORE_IMAGE="$ANCHORE_IMAGE"
    if [ -f "$TOOL_SCRIPTS_DIR/run_anchore.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_anchore.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_anchore.sh"; then
            log_message "run_anchore.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Anchore"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_anchore.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Anchore"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_anchore.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Anchore Scan Orchestration Finished ---"
else
    if [ "$SCAN_TYPE" = "code" ]; then
        log_message "--- Skipping Anchore Scan (no container image specified) ---"
    else
        log_message "--- Skipping Anchore Scan (Website scan mode) ---"
    fi
fi

# Only run CodeQL for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_codeql.sh
    log_message "--- Orchestrating CodeQL Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export CODEQL_CONFIG_PATH="$CODEQL_CONFIG_PATH_IN_CONTAINER"
    export CODEQL_QUERIES_PATH="$CODEQL_QUERIES_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_codeql.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_codeql.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_codeql.sh"; then
            log_message "run_codeql.sh completed successfully (exit code 0)."
            SCANNER_STATUS["CodeQL"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_codeql.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["CodeQL"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_codeql.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- CodeQL Scan Orchestration Finished ---"
else
    log_message "--- Skipping CodeQL Scan (Website scan mode) ---"
fi

# Only run OWASP Dependency Check for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_owasp_dependency_check.sh
    log_message "--- Orchestrating OWASP Dependency Check Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export OWASP_DC_CONFIG_PATH="$OWASP_DC_CONFIG_PATH_IN_CONTAINER"
    export OWASP_DC_DATA_DIR="$OWASP_DC_DATA_DIR_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh"; then
            log_message "run_owasp_dependency_check.sh completed successfully (exit code 0)."
            SCANNER_STATUS["OWASP_DC"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_owasp_dependency_check.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["OWASP_DC"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_owasp_dependency_check.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- OWASP Dependency Check Scan Orchestration Finished ---"
else
    log_message "--- Skipping OWASP Dependency Check Scan (Website scan mode) ---"
fi

# Only run Safety for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_safety.sh
    log_message "--- Orchestrating Safety Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export SAFETY_CONFIG_PATH="$SAFETY_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_safety.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_safety.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_safety.sh"; then
            log_message "run_safety.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Safety"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_safety.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Safety"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_safety.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Safety Scan Orchestration Finished ---"
else
    log_message "--- Skipping Safety Scan (Website scan mode) ---"
fi

# Only run Snyk for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_snyk.sh
    log_message "--- Orchestrating Snyk Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export SNYK_CONFIG_PATH="$SNYK_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_snyk.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_snyk.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_snyk.sh"; then
            log_message "run_snyk.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Snyk"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_snyk.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Snyk"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_snyk.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Snyk Scan Orchestration Finished ---"
else
    log_message "--- Skipping Snyk Scan (Website scan mode) ---"
fi

# Only run SonarQube for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_sonarqube.sh
    log_message "--- Orchestrating SonarQube Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export SONARQUBE_CONFIG_PATH="$SONARQUBE_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_sonarqube.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_sonarqube.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_sonarqube.sh"; then
            log_message "run_sonarqube.sh completed successfully (exit code 0)."
            SCANNER_STATUS["SonarQube"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_sonarqube.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["SonarQube"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_sonarqube.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- SonarQube Scan Orchestration Finished ---"
else
    log_message "--- Skipping SonarQube Scan (Website scan mode) ---"
fi

# Only run Terraform security scan for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_terraform_security.sh
    log_message "--- Orchestrating Terraform Security Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export TERRAFORM_SECURITY_CONFIG_PATH="$TERRAFORM_SECURITY_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_terraform_security.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_terraform_security.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_terraform_security.sh"; then
            log_message "run_terraform_security.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Terraform"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_terraform_security.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Terraform"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_terraform_security.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Terraform Security Scan Orchestration Finished ---"
else
    log_message "--- Skipping Terraform Security Scan (Website scan mode) ---"
fi

# Only run Checkov for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_checkov.sh
    log_message "--- Orchestrating Checkov Infrastructure Security Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export CHECKOV_CONFIG_PATH="$CHECKOV_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_checkov.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_checkov.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_checkov.sh"; then
            log_message "run_checkov.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Checkov"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_checkov.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Checkov"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_checkov.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Checkov Infrastructure Security Scan Orchestration Finished ---"
else
    log_message "--- Skipping Checkov Infrastructure Security Scan (Website scan mode) ---"
fi

# Only run TruffleHog for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_trufflehog.sh
    log_message "--- Orchestrating TruffleHog Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export TRUFFLEHOG_CONFIG_PATH="$TRUFFLEHOG_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_trufflehog.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_trufflehog.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_trufflehog.sh"; then
            log_message "run_trufflehog.sh completed successfully (exit code 0)."
            SCANNER_STATUS["TruffleHog"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_trufflehog.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["TruffleHog"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_trufflehog.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- TruffleHog Scan Orchestration Finished ---"
else
    log_message "--- Skipping TruffleHog Scan (Website scan mode) ---"
fi

# Only run GitLeaks for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_gitleaks.sh
    log_message "--- Orchestrating GitLeaks Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export GITLEAKS_CONFIG_PATH="$GITLEAKS_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_gitleaks.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_gitleaks.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_gitleaks.sh"; then
            log_message "run_gitleaks.sh completed successfully (exit code 0)."
            SCANNER_STATUS["GitLeaks"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_gitleaks.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["GitLeaks"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_gitleaks.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- GitLeaks Scan Orchestration Finished ---"
else
    log_message "--- Skipping GitLeaks Scan (Website scan mode) ---"
fi

# Only run Detect-secrets for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_detect_secrets.sh
    log_message "--- Orchestrating Detect-secrets Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export DETECT_SECRETS_CONFIG_PATH="$DETECT_SECRETS_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_detect_secrets.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_detect_secrets.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_detect_secrets.sh"; then
            log_message "run_detect_secrets.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Detect-secrets"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_detect_secrets.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Detect-secrets"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_detect_secrets.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Detect-secrets Scan Orchestration Finished ---"
else
    log_message "--- Skipping Detect-secrets Scan (Website scan mode) ---"
fi

# Only run npm audit for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_npm_audit.sh
    log_message "--- Orchestrating npm audit Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export NPM_AUDIT_CONFIG_PATH="$NPM_AUDIT_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_npm_audit.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_npm_audit.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_npm_audit.sh"; then
            log_message "run_npm_audit.sh completed successfully (exit code 0)."
            SCANNER_STATUS["npm_audit"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_npm_audit.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["npm_audit"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_npm_audit.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- npm audit Scan Orchestration Finished ---"
else
    log_message "--- Skipping npm audit Scan (Website scan mode) ---"
fi

# Only run Kube-hunter for network scans
if [ "$SCAN_TYPE" = "network" ]; then
    # Set environment variables specifically for run_kube_hunter.sh
    log_message "--- Orchestrating Kube-hunter Scan ---"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export KUBE_HUNTER_CONFIG_PATH="$KUBE_HUNTER_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_kube_hunter.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_kube_hunter.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_kube_hunter.sh"; then
            log_message "run_kube_hunter.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Kube-hunter"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_kube_hunter.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Kube-hunter"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_kube_hunter.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Kube-hunter Scan Orchestration Finished ---"
fi

# Only run Kube-bench for network scans
if [ "$SCAN_TYPE" = "network" ]; then
    # Set environment variables specifically for run_kube_bench.sh
    log_message "--- Orchestrating Kube-bench Scan ---"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export KUBE_BENCH_CONFIG_PATH="$KUBE_BENCH_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_kube_bench.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_kube_bench.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_kube_bench.sh"; then
            log_message "run_kube_bench.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Kube-bench"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_kube_bench.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Kube-bench"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_kube_bench.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Kube-bench Scan Orchestration Finished ---"
fi

# Only run Docker Bench for network scans
if [ "$SCAN_TYPE" = "network" ]; then
    # Set environment variables specifically for run_docker_bench.sh
    log_message "--- Orchestrating Docker Bench Scan ---"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export DOCKER_BENCH_CONFIG_PATH="$DOCKER_BENCH_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_docker_bench.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_docker_bench.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_docker_bench.sh"; then
            log_message "run_docker_bench.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Docker_bench"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_docker_bench.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Docker_bench"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_docker_bench.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Docker Bench Scan Orchestration Finished ---"
fi

# Only run ESLint for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_eslint.sh
    log_message "--- Orchestrating ESLint Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export ESLINT_CONFIG_PATH="$ESLINT_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_eslint.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_eslint.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_eslint.sh"; then
            log_message "run_eslint.sh completed successfully (exit code 0)."
            SCANNER_STATUS["ESLint"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_eslint.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["ESLint"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_eslint.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- ESLint Scan Orchestration Finished ---"
else
    log_message "--- Skipping ESLint Scan (Website scan mode) ---"
fi

# Only run Brakeman for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_brakeman.sh
    log_message "--- Orchestrating Brakeman Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export BRAKEMAN_CONFIG_PATH="$BRAKEMAN_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_brakeman.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_brakeman.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_brakeman.sh"; then
            log_message "run_brakeman.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Brakeman"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_brakeman.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Brakeman"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_brakeman.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Brakeman Scan Orchestration Finished ---"
else
    log_message "--- Skipping Brakeman Scan (Website scan mode) ---"
fi

# Only run Bandit for code scans
if [ "$SCAN_TYPE" = "code" ]; then
    # Set environment variables specifically for run_bandit.sh
    log_message "--- Orchestrating Bandit Scan ---"
    export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    export BANDIT_CONFIG_PATH="$BANDIT_CONFIG_PATH_IN_CONTAINER"
    if [ -f "$TOOL_SCRIPTS_DIR/run_bandit.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_bandit.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_bandit.sh"; then
            log_message "run_bandit.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Bandit"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_bandit.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Bandit"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_bandit.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Bandit Scan Orchestration Finished ---"
else
    log_message "--- Skipping Bandit Scan (Website scan mode) ---"
fi

# Only run native app scanners for code scans with detected native projects
if [ "$SCAN_TYPE" = "code" ]; then
    log_message "--- Detecting Native Mobile App Projects ---"
    IS_NATIVE=$(python3 "$BASE_PROJECT_DIR/scripts/project_detector.py" --target "$TARGET_PATH_IN_CONTAINER" --format json | jq -r '.has_native' 2>/dev/null || echo "false")
    
    if [ "$IS_NATIVE" = "true" ]; then
        log_message "--- Native app project detected, running mobile scanners ---"
        
        # Run Android Manifest Scanner
        log_message "--- Orchestrating Android Manifest Scan ---"
        export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
        export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
        if [ -f "$TOOL_SCRIPTS_DIR/run_android_manifest_scanner.sh" ]; then
            log_message "Executing $TOOL_SCRIPTS_DIR/run_android_manifest_scanner.sh..."
            if /bin/bash "$TOOL_SCRIPTS_DIR/run_android_manifest_scanner.sh"; then
                log_message "run_android_manifest_scanner.sh completed successfully (exit code 0)."
                SCANNER_STATUS["Android"]="SUCCESS"
            else
                EXIT_CODE=$?
                log_message "[ORCHESTRATOR ERROR] run_android_manifest_scanner.sh failed with exit code $EXIT_CODE."
                SCANNER_STATUS["Android"]="FAILED"
                OVERALL_SUCCESS=false
            fi
        else
            log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_android_manifest_scanner.sh not found!"
            OVERALL_SUCCESS=false
        fi
        log_message "--- Android Manifest Scan Orchestration Finished ---"
        
        # Run iOS Plist Scanner
        log_message "--- Orchestrating iOS Plist Scan ---"
        export TARGET_PATH="$TARGET_PATH_IN_CONTAINER"
        export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
        if [ -f "$TOOL_SCRIPTS_DIR/run_ios_plist_scanner.sh" ]; then
            log_message "Executing $TOOL_SCRIPTS_DIR/run_ios_plist_scanner.sh..."
            if /bin/bash "$TOOL_SCRIPTS_DIR/run_ios_plist_scanner.sh"; then
                log_message "run_ios_plist_scanner.sh completed successfully (exit code 0)."
                SCANNER_STATUS["iOS"]="SUCCESS"
            else
                EXIT_CODE=$?
                log_message "[ORCHESTRATOR ERROR] run_ios_plist_scanner.sh failed with exit code $EXIT_CODE."
                SCANNER_STATUS["iOS"]="FAILED"
                OVERALL_SUCCESS=false
            fi
        else
            log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_ios_plist_scanner.sh not found!"
            OVERALL_SUCCESS=false
        fi
        log_message "--- iOS Plist Scan Orchestration Finished ---"
    else
        log_message "--- No native app project detected, skipping mobile scanners ---"
    fi
else
    log_message "--- Skipping Native App Scanners (Website scan mode) ---"
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
            SCANNER_STATUS["ZAP"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_zap.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["ZAP"]="FAILED"
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

# Only run Nuclei for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_nuclei.sh
    log_message "--- Orchestrating Nuclei Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export NUCLEI_CONFIG_PATH="$BASE_PROJECT_DIR/nuclei/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_nuclei.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_nuclei.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_nuclei.sh"; then
            log_message "run_nuclei.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Nuclei"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_nuclei.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Nuclei"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_nuclei.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Nuclei Scan Orchestration Finished ---"
else
    log_message "--- Skipping Nuclei Scan (Code scan mode) ---"
fi

# Only run Wapiti for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_wapiti.sh
    log_message "--- Orchestrating Wapiti Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export WAPITI_CONFIG_PATH="$BASE_PROJECT_DIR/wapiti/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_wapiti.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_wapiti.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_wapiti.sh"; then
            log_message "run_wapiti.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Wapiti"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_wapiti.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Wapiti"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_wapiti.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Wapiti Scan Orchestration Finished ---"
else
    log_message "--- Skipping Wapiti Scan (Code scan mode) ---"
fi

# Only run Nikto for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_nikto.sh
    log_message "--- Orchestrating Nikto Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export NIKTO_CONFIG_PATH="$BASE_PROJECT_DIR/nikto/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_nikto.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_nikto.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_nikto.sh"; then
            log_message "run_nikto.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Nikto"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_nikto.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Nikto"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_nikto.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Nikto Scan Orchestration Finished ---"
else
    log_message "--- Skipping Nikto Scan (Code scan mode) ---"
fi

# Only run Burp Suite for website scans
if [ "$SCAN_TYPE" = "website" ]; then
    # Set environment variables specifically for run_burp.sh
    log_message "--- Orchestrating Burp Suite Scan ---"
    # ZAP_TARGET is exported
    export RESULTS_DIR="$RESULTS_DIR_IN_CONTAINER"
    # LOG_FILE is exported
    export BURP_CONFIG_PATH="$BASE_PROJECT_DIR/burp/config.yaml"
    if [ -f "$TOOL_SCRIPTS_DIR/run_burp.sh" ]; then
        log_message "Executing $TOOL_SCRIPTS_DIR/run_burp.sh..."
        if /bin/bash "$TOOL_SCRIPTS_DIR/run_burp.sh"; then
            log_message "run_burp.sh completed successfully (exit code 0)."
            SCANNER_STATUS["Burp"]="SUCCESS"
        else
            EXIT_CODE=$?
            log_message "[ORCHESTRATOR ERROR] run_burp.sh failed with exit code $EXIT_CODE."
            SCANNER_STATUS["Burp"]="FAILED"
            OVERALL_SUCCESS=false
        fi
    else
        log_message "[ORCHESTRATOR ERROR] $TOOL_SCRIPTS_DIR/run_burp.sh not found!"
        OVERALL_SUCCESS=false
    fi
    log_message "--- Burp Suite Scan Orchestration Finished ---"
else
    log_message "--- Skipping Burp Suite Scan (Code scan mode) ---"
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
    # Export OUTPUT_FILE so the Python script knows where the output should be
    export OUTPUT_FILE="$HTML_REPORT_OUTPUT_FILE"
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
log_message ""
log_message "=============================================="
log_message "         SCAN SUMMARY & RESULTS"
log_message "=============================================="
log_message ""

# Generate detailed summary of all scanners with actual status
log_message "Scanner Status Summary (from scan execution):"
log_message "  Semgrep:       ${SCANNER_STATUS[Semgrep]:-N/A}"
log_message "  Trivy:         ${SCANNER_STATUS[Trivy]:-N/A}"
log_message "  CodeQL:        ${SCANNER_STATUS[CodeQL]:-N/A}"
log_message "  OWASP_DC:      ${SCANNER_STATUS[OWASP_DC]:-N/A}"
log_message "  Safety:        ${SCANNER_STATUS[Safety]:-N/A}"
log_message "  Snyk:          ${SCANNER_STATUS[Snyk]:-N/A}"
log_message "  SonarQube:     ${SCANNER_STATUS[SonarQube]:-N/A}"
log_message "  Checkov:       ${SCANNER_STATUS[Checkov]:-N/A}"
log_message "  TruffleHog:    ${SCANNER_STATUS[TruffleHog]:-N/A}"
log_message "  GitLeaks:      ${SCANNER_STATUS[GitLeaks]:-N/A}"
log_message "  Detect-secrets:${SCANNER_STATUS[Detect-secrets]:-N/A}"
log_message "  npm_audit:     ${SCANNER_STATUS[npm_audit]:-N/A}"
log_message "  ESLint:        ${SCANNER_STATUS[ESLint]:-N/A}"
log_message "  Brakeman:      ${SCANNER_STATUS[Brakeman]:-N/A}"
log_message "  Bandit:        ${SCANNER_STATUS[Bandit]:-N/A}"
log_message "  Android:       ${SCANNER_STATUS[Android]:-N/A}"
log_message "  iOS:           ${SCANNER_STATUS[iOS]:-N/A}"
log_message "  ZAP:           ${SCANNER_STATUS[ZAP]:-N/A}"
log_message "  Nuclei:        ${SCANNER_STATUS[Nuclei]:-N/A}"
log_message "  Wapiti:        ${SCANNER_STATUS[Wapiti]:-N/A}"
log_message "  Nikto:         ${SCANNER_STATUS[Nikto]:-N/A}"
log_message "  Burp:          ${SCANNER_STATUS[Burp]:-N/A}"
log_message "  Clair:         ${SCANNER_STATUS[Clair]:-N/A}"
log_message "  Anchore:       ${SCANNER_STATUS[Anchore]:-N/A}"
log_message "  Terraform:     ${SCANNER_STATUS[Terraform]:-N/A}"
log_message "  Kube-hunter:   ${SCANNER_STATUS[Kube-hunter]:-N/A}"
log_message "  Kube-bench:    ${SCANNER_STATUS[Kube-bench]:-N/A}"
log_message "  Docker_bench:  ${SCANNER_STATUS[Docker_bench]:-N/A}"
log_message ""
log_message "Note: SKIPPED = Not applicable to this scan type"
log_message "      SUCCESS  = Scan completed successfully"
log_message "      FAILED   = Scan encountered errors (see log above)"
log_message ""

log_message "Key Results Location:"
log_message "  📊 HTML Report: $RESULTS_DIR_IN_CONTAINER/security-summary.html"
log_message "  📝 Full Log: $LOG_FILE"
log_message ""

if [ "$OVERALL_SUCCESS" = true ]; then
    log_message "✅ [FINAL STATUS: SUCCESS] All enabled scans completed successfully."
else
    log_message "⚠️  [FINAL STATUS: FAILED] One or more scan steps encountered errors."
fi
log_message "=============================================="

if [ "$OVERALL_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi 