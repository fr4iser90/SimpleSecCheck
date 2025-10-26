#!/bin/bash
# Individual ZAP Scan Script for SimpleSecCheck Plugin System (v6 - Reintroducing targeted find for reports)

set -e # Exit immediately if a command exits with a non-zero status.

# Expected Environment Variables:
# ZAP_TARGET: Target URL for ZAP (e.g., http://host.docker.internal:8000)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)
# ZAP_STARTUP_DELAY: Optional delay in seconds to wait for target to be ready (default 25)

ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:8000}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}" # This is an absolute path like /SimpleSecCheck/results
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
ZAP_STARTUP_DELAY="${ZAP_STARTUP_DELAY:-25}"

SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

log_zap_action() {
    echo "[run_zap.sh] ($(date '+%Y-%m-%d %H:%M:%S')) ($BASHPID) $1" | tee -a "$LOG_FILE"
}

log_zap_action "Initializing ZAP scan (v6 - Reintroducing targeted find for reports)..."
log_zap_action "ZAP Target: $ZAP_TARGET"
log_zap_action "Expected Results Directory: $RESULTS_DIR"
log_zap_action "Log File: $LOG_FILE"
log_zap_action "Startup Delay: $ZAP_STARTUP_DELAY seconds"

if ! command -v python3 &>/dev/null; then
  log_zap_action "[ERROR] python3 is not installed or not in PATH. ZAP scan cannot run."
  exit 1
fi
ZAP_BASELINE_SCRIPT=$(command -v zap-baseline.py)
if [ -z "$ZAP_BASELINE_SCRIPT" ]; then
  log_zap_action "[ERROR] zap-baseline.py not found. ZAP scan cannot run."
  exit 1
fi
log_zap_action "Using ZAP baseline script at: $ZAP_BASELINE_SCRIPT"

if [ "$ZAP_STARTUP_DELAY" -gt 0 ]; then
    log_zap_action "Waiting $ZAP_STARTUP_DELAY seconds for target application ($ZAP_TARGET) to start..."
    sleep "$ZAP_STARTUP_DELAY"
fi

if command -v curl &>/dev/null; then
    log_zap_action "Checking reachability of ZAP target $ZAP_TARGET with curl..."
    if curl --output /dev/null --silent --head --fail --max-time 15 "$ZAP_TARGET"; then
        log_zap_action "Successfully connected to $ZAP_TARGET."
    else
        CURL_EXIT_CODE=$?
        log_zap_action "[ERROR] Failed to connect to $ZAP_TARGET with curl (Exit Code: $CURL_EXIT_CODE). ZAP scan may fail or produce limited results. Proceeding anyway..."
    fi
else
    log_zap_action "[WARN] curl not found. Skipping target reachability check for $ZAP_TARGET."
fi

export ZAP_PATH=${ZAP_PATH:-/opt/ZAP_2.16.1}
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}

log_zap_action "[ZAP ENV] ZAP_PATH=$ZAP_PATH, JAVA_HOME=$JAVA_HOME"
log_zap_action "[ZAP] Starting DEEP baseline scan on $ZAP_TARGET with aggressive policies..."

# Set ZAP to use more aggressive scanning policies for deeper analysis
export ZAP_OPTIONS="-config api.disablekey=true -config spider.maxDuration=10 -config scanner.maxDuration=30 -config scanner.maxRuleTimeInMs=60000"

# Expected absolute paths for final reports
ZAP_REPORT_XML_ABS="$RESULTS_DIR/zap-report.xml"
ZAP_REPORT_HTML_ABS="$RESULTS_DIR/zap-report.html"

rm -f "$ZAP_REPORT_XML_ABS" "$ZAP_REPORT_HTML_ABS"
log_zap_action "Removed any pre-existing $ZAP_REPORT_XML_ABS and $ZAP_REPORT_HTML_ABS from $RESULTS_DIR"

XML_GENERATED=false
HTML_GENERATED=false

ORIGINAL_PWD=$(pwd)
log_zap_action "Current PWD before ZAP XML: $ORIGINAL_PWD. Changing to $RESULTS_DIR for ZAP execution."
cd "$RESULTS_DIR"

# Attempt to generate reports using relative names, assuming ZAP writes to CWD ($RESULTS_DIR)
# Deep scan with aggressive spider and scanner settings
log_zap_action "[ZAP CMD XML] Executing DEEP scan from $(pwd): python3 $ZAP_BASELINE_SCRIPT -d -t \"$ZAP_TARGET\" -x \"zap-report.xml\" -J -a"
if python3 "$ZAP_BASELINE_SCRIPT" -d -t "$ZAP_TARGET" -x "zap-report.xml" -J -a 2>/dev/null; then
    log_zap_action "[ZAP CMD XML] zap-baseline.py for XML exited with 0."
else
    ZAP_XML_EXIT_CODE=$?
    log_zap_action "[ZAP CMD XML WARN] zap-baseline.py for XML exited with $ZAP_XML_EXIT_CODE."
fi

log_zap_action "[ZAP CMD HTML] Executing DEEP scan from $(pwd): python3 $ZAP_BASELINE_SCRIPT -d -t \"$ZAP_TARGET\" -f html -o \"zap-report.html\" -J -a"
if python3 "$ZAP_BASELINE_SCRIPT" -d -t "$ZAP_TARGET" -f html -o "zap-report.html" -J -a 2>/dev/null; then
    log_zap_action "[ZAP CMD HTML] zap-baseline.py for HTML exited with 0."
else
    ZAP_HTML_EXIT_CODE=$?
    log_zap_action "[ZAP CMD HTML WARN] zap-baseline.py for HTML exited with $ZAP_HTML_EXIT_CODE."
fi

log_zap_action "Returning to PWD: $ORIGINAL_PWD from $RESULTS_DIR"
cd "$ORIGINAL_PWD"

# Check if reports were created in RESULTS_DIR as expected
if [ -f "$ZAP_REPORT_XML_ABS" ]; then
    log_zap_action "[Primary Check] XML report $ZAP_REPORT_XML_ABS found in $RESULTS_DIR."
    XML_GENERATED=true
else
    log_zap_action "[Primary Check] XML report $ZAP_REPORT_XML_ABS NOT found in $RESULTS_DIR directly."
fi

if [ -f "$ZAP_REPORT_HTML_ABS" ]; then
    log_zap_action "[Primary Check] HTML report $ZAP_REPORT_HTML_ABS found in $RESULTS_DIR."
    HTML_GENERATED=true
else
    log_zap_action "[Primary Check] HTML report $ZAP_REPORT_HTML_ABS NOT found in $RESULTS_DIR directly."
fi

# Fallback: Search common ZAP directories and copy if reports are missing from RESULTS_DIR
COMMON_ZAP_DIRS=("/home/zap/.ZAP/" "/zap/wrk/" "/tmp/") # Add other potential ZAP default dirs if known

if [ "$XML_GENERATED" = false ]; then
    log_zap_action "[Fallback Search XML] XML report was not in $RESULTS_DIR. Searching common ZAP locations..."
    for search_dir in "${COMMON_ZAP_DIRS[@]}"; do
        if [ -d "$search_dir" ]; then
            FOUND_XML_FALLBACK=$(find "$search_dir" -name 'zap-report.xml' -print -quit 2>/dev/null)
            if [ -n "$FOUND_XML_FALLBACK" ]; then
                log_zap_action "[Fallback Search XML] Found $FOUND_XML_FALLBACK. Copying to $ZAP_REPORT_XML_ABS..."
                cp "$FOUND_XML_FALLBACK" "$ZAP_REPORT_XML_ABS"
                XML_GENERATED=true
                break
            fi
        fi
    done
    if [ "$XML_GENERATED" = false ]; then # Broader search if still not found
        log_zap_action "[Fallback Search XML Broad] Still not found. Searching / (excluding $RESULTS_DIR)..."
        FOUND_XML_BROAD=$(find / -path "$RESULTS_DIR" -prune -o -name 'zap-report.xml' -print -quit 2>/dev/null)
        if [ -n "$FOUND_XML_BROAD" ]; then
            log_zap_action "[Fallback Search XML Broad] Found $FOUND_XML_BROAD. Copying to $ZAP_REPORT_XML_ABS..."
            cp "$FOUND_XML_BROAD" "$ZAP_REPORT_XML_ABS"
            XML_GENERATED=true
        fi
    fi
fi

if [ "$HTML_GENERATED" = false ]; then
    log_zap_action "[Fallback Search HTML] HTML report was not in $RESULTS_DIR. Searching common ZAP locations..."
    for search_dir in "${COMMON_ZAP_DIRS[@]}"; do
        if [ -d "$search_dir" ]; then
            FOUND_HTML_FALLBACK=$(find "$search_dir" -name 'zap-report.html' -print -quit 2>/dev/null)
            if [ -n "$FOUND_HTML_FALLBACK" ]; then
                log_zap_action "[Fallback Search HTML] Found $FOUND_HTML_FALLBACK. Copying to $ZAP_REPORT_HTML_ABS..."
                cp "$FOUND_HTML_FALLBACK" "$ZAP_REPORT_HTML_ABS"
                HTML_GENERATED=true
                break
            fi
        fi
    done
    if [ "$HTML_GENERATED" = false ]; then # Broader search if still not found
        log_zap_action "[Fallback Search HTML Broad] Still not found. Searching / (excluding $RESULTS_DIR)..."
        FOUND_HTML_BROAD=$(find / -path "$RESULTS_DIR" -prune -o -name 'zap-report.html' -print -quit 2>/dev/null)
        if [ -n "$FOUND_HTML_BROAD" ]; then
            log_zap_action "[Fallback Search HTML Broad] Found $FOUND_HTML_BROAD. Copying to $ZAP_REPORT_HTML_ABS..."
            cp "$FOUND_HTML_BROAD" "$ZAP_REPORT_HTML_ABS"
            HTML_GENERATED=true
        fi
    fi
fi

log_zap_action "[ZAP Debug] Final listing of $RESULTS_DIR after fallbacks:"
ls -l "$RESULTS_DIR" | tee -a "$LOG_FILE"

if [ "$XML_GENERATED" = true ] || [ "$HTML_GENERATED" = true ]; then
    log_zap_action "[ZAP SUCCESS] At least one ZAP report (XML or HTML) was found/copied to $RESULTS_DIR."
    [ "$XML_GENERATED" = true ] && log_zap_action "  - XML: $ZAP_REPORT_XML_ABS"
    [ "$HTML_GENERATED" = true ] && log_zap_action "  - HTML: $ZAP_REPORT_HTML_ABS"
    echo "[ZAP] Baseline scan complete." >> "$SUMMARY_TXT"
    log_zap_action "ZAP scan script finished successfully."
    exit 0
else
    log_zap_action "[ZAP FAILURE] NO ZAP report (XML or HTML) was found in $RESULTS_DIR even after fallback searches."
    exit 1
fi 