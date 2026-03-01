#!/bin/bash
# SimpleSecCheck - OWASP Dependency Check Database Update Script
# Updates the cached vulnerability database without running a scan
# Usage:
#   ./scripts/update-owasp-db.sh
#   NVD_API_KEY=your-key ./scripts/update-owasp-db.sh  # With API key for faster updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OWASP_DC_DATA_DIR="${OWASP_DC_DATA_DIR:-$SCRIPT_DIR/owasp-dependency-check-data}"
LOG_FILE="${LOG_FILE:-$SCRIPT_DIR/logs/owasp-update.log}"
DOCKER_IMAGE="${DOCKER_IMAGE:-fr4iser/simpleseccheck:latest}"

log_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

print_usage() {
    echo "Usage: $0"
    echo ""
    echo "Updates the OWASP Dependency Check vulnerability database."
    echo "This may take 5-15 minutes depending on your connection."
    echo ""
    echo "Environment Variables:"
    echo "  NVD_API_KEY          - NVD API key for faster updates (optional)"
    echo "  OWASP_DC_DATA_DIR    - Custom data directory (default: ./owasp-dependency-check-data)"
    echo "  DOCKER_IMAGE         - Docker image to use (default: fr4iser/simpleseccheck:latest)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Update without API key"
    echo "  NVD_API_KEY=your-key $0              # Update with API key"
    echo "  OWASP_DC_DATA_DIR=/custom/path $0    # Use custom data directory"
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_usage
    exit 0
fi

# Create directories
mkdir -p "$OWASP_DC_DATA_DIR" "$(dirname "$LOG_FILE")"

# Load optional API tokens from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    log_message "Loading API tokens from .env file..."
    set -a  # Export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # Stop automatically exporting
fi

# Check database status and age
check_database_status() {
    if [ ! -d "$OWASP_DC_DATA_DIR" ] || [ -z "$(ls -A "$OWASP_DC_DATA_DIR" 2>/dev/null)" ]; then
        echo "not_found"
        return
    fi
    
    # Find the most recent file in the database directory (usually the H2 database file)
    LATEST_FILE=$(find "$OWASP_DC_DATA_DIR" -type f -name "*.mv.db" -o -name "*.h2.db" -o -name "*.lock" 2>/dev/null | head -1)
    
    if [ -z "$LATEST_FILE" ]; then
        # Fallback: find any file
        LATEST_FILE=$(find "$OWASP_DC_DATA_DIR" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    fi
    
    if [ -n "$LATEST_FILE" ] && [ -f "$LATEST_FILE" ]; then
        # Get file modification time
        if command -v stat &> /dev/null; then
            # Linux
            FILE_TIME=$(stat -c %Y "$LATEST_FILE" 2>/dev/null || echo "0")
        else
            # macOS/BSD
            FILE_TIME=$(stat -f %m "$LATEST_FILE" 2>/dev/null || echo "0")
        fi
        
        if [ "$FILE_TIME" != "0" ]; then
            CURRENT_TIME=$(date +%s)
            AGE_SECONDS=$((CURRENT_TIME - FILE_TIME))
            AGE_DAYS=$((AGE_SECONDS / 86400))
            echo "$AGE_DAYS"
            return
        fi
    fi
    
    echo "unknown"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker image exists locally, otherwise pull it
if ! docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
    log_message "Docker image not found locally, pulling $DOCKER_IMAGE..."
    docker pull "$DOCKER_IMAGE" || {
        log_error "Failed to pull Docker image: $DOCKER_IMAGE"
        exit 1
    }
fi

# Prepare NVD API key flag
NVD_FLAG=""
if [ -n "$NVD_API_KEY" ]; then
    log_message "Using NVD_API_KEY for faster updates..."
    NVD_FLAG="--nvdApiKey=$NVD_API_KEY"
else
    log_warning "No NVD_API_KEY provided, using public rate limits (slower)..."
    log_warning "Tip: Set NVD_API_KEY in .env file or as environment variable for faster updates"
    log_warning "Get your free API key from: https://nvd.nist.gov/developers/request-an-api-key"
fi

# Check database status
DB_STATUS=$(check_database_status)

echo ""
echo "=========================================="
echo -e "${GREEN}🔄 OWASP Dependency Check Database Update${NC}"
echo "=========================================="
echo -e "📂 Data Directory: ${GREEN}$OWASP_DC_DATA_DIR${NC}"
echo -e "🐳 Docker Image: ${GREEN}$DOCKER_IMAGE${NC}"
if [ -n "$NVD_API_KEY" ]; then
    echo -e "🔑 NVD API Key: ${GREEN}Provided${NC}"
else
    echo -e "🔑 NVD API Key: ${YELLOW}Not provided${NC}"
fi

# Display database status
case "$DB_STATUS" in
    "not_found")
        echo -e "📊 Database Status: ${YELLOW}Not found${NC} (will be created)"
        ;;
    "unknown")
        echo -e "📊 Database Status: ${YELLOW}Found (age unknown)${NC}"
        ;;
    *)
        if [ "$DB_STATUS" -lt 1 ]; then
            echo -e "📊 Database Status: ${GREEN}Up to date${NC} (less than 1 day old)"
        elif [ "$DB_STATUS" -lt 7 ]; then
            echo -e "📊 Database Status: ${GREEN}Recent${NC} ($DB_STATUS days old)"
        elif [ "$DB_STATUS" -lt 30 ]; then
            echo -e "📊 Database Status: ${YELLOW}Moderate${NC} ($DB_STATUS days old)"
        else
            echo -e "📊 Database Status: ${RED}Outdated${NC} ($DB_STATUS days old - update recommended!)"
        fi
        ;;
esac
echo ""

# Note: OWASP Dependency Check's --updateonly is intelligent and only downloads
# changed data, so it's safe to run even if the database is recent.
log_message "Starting database update..."
log_message "Note: OWASP Dependency Check will only download changed data (incremental update)"
log_message "This may take 5-15 minutes depending on your connection and how much data has changed..."
echo ""

# Run update in Docker container
if docker run --rm \
    -v "$OWASP_DC_DATA_DIR:/SimpleSecCheck/owasp-dependency-check-data" \
    -e NVD_API_KEY="${NVD_API_KEY:-}" \
    "$DOCKER_IMAGE" \
    dependency-check --updateonly --data /SimpleSecCheck/owasp-dependency-check-data $NVD_FLAG 2>&1 | tee "$LOG_FILE"; then
    
    echo ""
    log_success "✅ Database update completed successfully!"
    log_message "Updated database location: $OWASP_DC_DATA_DIR"
    log_message "Log file: $LOG_FILE"
    echo ""
    exit 0
else
    EXIT_CODE=${PIPESTATUS[0]}
    echo ""
    log_warning "⚠️  Update completed with warnings or errors (exit code: $EXIT_CODE)"
    log_message "Check log file for details: $LOG_FILE"
    echo ""
    exit $EXIT_CODE
fi
