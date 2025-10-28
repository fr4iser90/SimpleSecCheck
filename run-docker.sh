#!/bin/bash
# SimpleSecCheck - Docker Single-Shot Security Scanner
# Usage: 
#   ./run-docker.sh <target-path>                    # Scan local code
#   ./run-docker.sh <website-url>                    # Scan website
# Examples:
#   ./run-docker.sh /home/user/my-project
#   ./run-docker.sh https://fr4iser.com
#   ./run-docker.sh network                              # Scan network/infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$1"

# Determine scan type
if [ "$TARGET" = "network" ]; then
    # Network/infrastructure scan
    SCAN_TYPE="network"
    TARGET_PATH=""
    ZAP_TARGET=""
    PROJECT_NAME="network-infrastructure"
elif [[ "$TARGET" =~ ^https?:// ]]; then
    # Website scan
    SCAN_TYPE="website"
    ZAP_TARGET="$TARGET"
    TARGET_PATH=""
    PROJECT_NAME=$(echo "$TARGET" | sed 's|https\?://||' | sed 's|/.*||' | sed 's|:.*||')
else
    # Code scan
    SCAN_TYPE="code"
    TARGET_PATH="$TARGET"
    ZAP_TARGET=""
    PROJECT_NAME=$(basename "$TARGET")
fi

# Add timestamp for uniqueness
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PROJECT_DIR="${PROJECT_NAME}_${TIMESTAMP}"

RESULTS_DIR="$SCRIPT_DIR/results/$PROJECT_DIR"
LOGS_DIR="$SCRIPT_DIR/results/$PROJECT_DIR/logs"

# Store original for later reference
OVERALL_SUCCESS=false

# Functions
log_message() {
    echo -e "${BLUE}[SimpleSecCheck Docker]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if target is provided
if [ -z "$TARGET" ]; then
    echo "Usage: $0 <target>"
    echo ""
    echo "Examples:"
    echo "  $0 /home/user/my-project          # Scan local code"
    echo "  $0 https://fr4iser.com            # Scan website"
    echo "  $0 network                        # Scan network/infrastructure"
    exit 1
fi

# Check if target path exists (only for code scans)
if [ "$SCAN_TYPE" = "code" ] && [ ! -d "$TARGET_PATH" ] && [ ! -f "$TARGET_PATH" ]; then
    log_error "Target path does not exist: $TARGET_PATH"
    exit 1
fi

# Create directories
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

echo ""
echo -e "${BLUE}🚀 SimpleSecCheck Docker Security Scanner${NC}"
echo "=========================================="
echo -e "🎯 Scan Type: ${GREEN}$SCAN_TYPE${NC}"
if [ "$SCAN_TYPE" = "code" ]; then
    echo -e "📁 Target: ${GREEN}$TARGET_PATH${NC}"
else
    echo -e "🌐 Target: ${GREEN}$ZAP_TARGET${NC}"
fi
echo -e "📂 Project: ${GREEN}$PROJECT_NAME${NC}"
echo -e "📊 Results: ${GREEN}$RESULTS_DIR${NC}"
echo ""

log_message "Starting Docker container for security scan..."

# Set environment variables for Docker
export TARGET_URL="$ZAP_TARGET"
export ZAP_TARGET="$ZAP_TARGET"
export TARGET_PATH_IN_CONTAINER="/target"
export PROJECT_RESULTS_DIR="$RESULTS_DIR"
export SCAN_TYPE="$SCAN_TYPE"

# Load optional API tokens from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}[INFO]${NC} Loading API tokens from .env file..."
    set -a  # Export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # Stop automatically exporting
fi

# Run Docker Compose with the scanner service
if [ "$SCAN_TYPE" = "network" ]; then
    # Network scan: needs docker socket for docker-bench
    if docker-compose -f docker-compose.yml run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        scanner /SimpleSecCheck/scripts/security-check.sh; then
        log_success "Network security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_warning "Network security scan completed with warnings"
        OVERALL_SUCCESS=false
    fi
elif [ "$SCAN_TYPE" = "code" ]; then
    # Code scan: mount code directory
    if docker-compose -f docker-compose.yml run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -v "$TARGET_PATH:/target:ro" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        scanner /SimpleSecCheck/scripts/security-check.sh; then
        log_success "Code security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_warning "Code security scan completed with warnings"
        OVERALL_SUCCESS=false
    fi
else
    # Website scan: no code mount needed
    if docker-compose -f docker-compose.yml run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        scanner /SimpleSecCheck/scripts/security-check.sh; then
        log_success "Website security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_warning "Website security scan completed with warnings"
        OVERALL_SUCCESS=false
    fi
fi

# Final status
echo ""
if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}✅ Security scan completed successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Security scan completed with warnings${NC}"
fi

echo ""
echo -e "${BLUE}📊 Results available in:${NC} $RESULTS_DIR"
echo -e "${BLUE}🌐 Open HTML report:${NC} file://$RESULTS_DIR/security-summary.html"
echo ""

# Show generated files
echo -e "${BLUE}📁 Generated Files:${NC}"
[ -f "$RESULTS_DIR/semgrep.json" ] && echo -e "  ${GREEN}✓${NC} Semgrep: $RESULTS_DIR/semgrep.json"
[ -f "$RESULTS_DIR/trivy.json" ] && echo -e "  ${GREEN}✓${NC} Trivy: $RESULTS_DIR/trivy.json"
[ -f "$RESULTS_DIR/zap-report.xml" ] && echo -e "  ${GREEN}✓${NC} ZAP: $RESULTS_DIR/zap-report.xml"
[ -f "$RESULTS_DIR/security-summary.html" ] && echo -e "  ${GREEN}✓${NC} HTML Report: $RESULTS_DIR/security-summary.html"
[ -f "$LOGS_DIR/security-check.log" ] && echo -e "  ${GREEN}✓${NC} Log File: $LOGS_DIR/security-check.log"

echo ""
log_message "SimpleSecCheck Docker Security Scan Completed: $(date)"
