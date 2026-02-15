#!/bin/bash
# SimpleSecCheck - Docker Single-Shot Security Scanner
# Usage:
#   ./run-docker.sh [--ci] <target-path>             # Scan local code
#   ./run-docker.sh [--ci] <website-url>             # Scan website
# Examples:
#   ./run-docker.sh /home/user/my-project
#   ./run-docker.sh --ci /home/user/my-project
#   ./run-docker.sh --finding-policy config/finding-policy.json /home/user/my-project
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCAN_SCOPE="${SCAN_SCOPE:-full}" # full | tracked
SIMPLESECCHECK_EXCLUDE_PATHS="${SIMPLESECCHECK_EXCLUDE_PATHS:-}"
CI_MODE=false
TARGET=""
FINDING_POLICY_ARG=""
FINDING_POLICY_FILE_IN_CONTAINER=""

print_usage() {
    echo "Usage: $0 [--ci] [--finding-policy <path>] <target>"
    echo ""
    echo "Examples:"
    echo "  $0 /home/user/my-project          # Scan local code"
    echo "  $0 --ci /home/user/my-project     # CI-friendly code scan"
    echo "  $0 --finding-policy config/finding-policy.json /home/user/my-project"
    echo "  $0 https://example.com            # Scan website"
    echo "  $0 network                        # Scan network/infrastructure"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --ci)
            CI_MODE=true
            shift
            ;;
        --finding-policy)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}[ERROR]${NC} Missing value for --finding-policy"
                print_usage
                exit 1
            fi
            FINDING_POLICY_ARG="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo -e "${RED}[ERROR]${NC} Unknown option: $1"
            print_usage
            exit 1
            ;;
        *)
            if [ -z "$TARGET" ]; then
                TARGET="$1"
                shift
            else
                echo -e "${RED}[ERROR]${NC} Unexpected extra argument: $1"
                print_usage
                exit 1
            fi
            ;;
    esac
done

if [ "$CI_MODE" = true ]; then
    SCAN_SCOPE="tracked"
    if [ -z "$SIMPLESECCHECK_EXCLUDE_PATHS" ]; then
        SIMPLESECCHECK_EXCLUDE_PATHS=".git,node_modules,dist,build,coverage,.next,.nuxt,.cache,results,logs,reddit-browser-data,browser-data,playwright-report,.scannerwork"
    fi
fi

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
    print_usage
    exit 1
fi

# Check if target path exists (only for code scans)
# Note: Skip validation if running inside a container (e.g., WebUI container)
# because host paths are not visible inside the container.
# Docker Compose will fail with a clear error if the path doesn't exist on the host.
if [ "$SCAN_TYPE" = "code" ]; then
    # Check if we're running in a container (e.g., WebUI container at /app)
    # If so, skip path validation - docker-compose will handle it
    if [ -d "/app" ] || [ -f "/.dockerenv" ]; then
        # Running in container: cannot validate host paths, let docker-compose handle it
        log_message "Running in container - path validation will be done by docker-compose when mounting"
    elif [ ! -d "$TARGET_PATH" ] && [ ! -f "$TARGET_PATH" ]; then
        # Running on host: validate path exists
        log_error "Target path does not exist: $TARGET_PATH"
        log_error "Please ensure the path exists on the host system"
        exit 1
    fi
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

# Determine docker-compose file and build context
# If running in container (e.g., WebUI), use /project as build context
# Otherwise use SCRIPT_DIR (host execution)
if [ -d "/project" ] && [ -f "/project/docker-compose.yml" ]; then
    # Running in container: use /project as build context
    DOCKER_COMPOSE_FILE="/project/docker-compose.yml"
    DOCKER_COMPOSE_CONTEXT="/project"
else
    # Running on host: use SCRIPT_DIR
    DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
    DOCKER_COMPOSE_CONTEXT="$SCRIPT_DIR"
fi

# Determine OWASP data volume mount (needed when using -v flags, as they override docker-compose.yml volumes)
if [ -d "/project" ] && [ -f "/project/docker-compose.yml" ]; then
    # Running in container: get host path
    log_message "[OWASP Volume] Running in container, determining host path..."
    
    # Method 1: Use environment variable if set
    if [ -n "$HOST_PROJECT_ROOT" ]; then
        log_message "[OWASP Volume] Using HOST_PROJECT_ROOT from environment: '$HOST_PROJECT_ROOT'"
    else
        # Method 2: Use docker inspect with container name
        CONTAINER_NAME="SimpleSecCheck_webui"
        log_message "[OWASP Volume] Trying container name: '$CONTAINER_NAME'"
        HOST_PROJECT_ROOT=$(docker inspect --format='{{range .Mounts}}{{if eq .Destination "/project"}}{{.Source}}{{end}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || echo "")
        log_message "[OWASP Volume] docker inspect result: HOST_PROJECT_ROOT='$HOST_PROJECT_ROOT'"
    fi
    if [ -n "$HOST_PROJECT_ROOT" ]; then
        OWASP_DATA_VOLUME="-v $HOST_PROJECT_ROOT/owasp-dependency-check-data:/SimpleSecCheck/owasp-dependency-check-data"
        log_message "[OWASP Volume] Using host path: $OWASP_DATA_VOLUME"
        log_message "[OWASP Volume] Checking if host path exists: $HOST_PROJECT_ROOT/owasp-dependency-check-data"
        if [ -d "$HOST_PROJECT_ROOT/owasp-dependency-check-data" ]; then
            log_message "[OWASP Volume] ✓ Host path exists"
        else
            log_warning "[OWASP Volume] ✗ Host path does NOT exist: $HOST_PROJECT_ROOT/owasp-dependency-check-data"
        fi
    else
        # Fallback: use relative path (might not work)
        OWASP_DATA_VOLUME="-v ./owasp-dependency-check-data:/SimpleSecCheck/owasp-dependency-check-data"
        log_warning "[OWASP Volume] Could not determine host project root, using relative path: $OWASP_DATA_VOLUME"
    fi
else
    # Running on host: use absolute path
    OWASP_DATA_VOLUME="-v $SCRIPT_DIR/owasp-dependency-check-data:/SimpleSecCheck/owasp-dependency-check-data"
    log_message "[OWASP Volume] Running on host, using absolute path: $OWASP_DATA_VOLUME"
    if [ -d "$SCRIPT_DIR/owasp-dependency-check-data" ]; then
        log_message "[OWASP Volume] ✓ Host path exists"
    else
        log_warning "[OWASP Volume] ✗ Host path does NOT exist: $SCRIPT_DIR/owasp-dependency-check-data"
    fi
fi

# Run Docker Compose with the scanner service
if [ "$SCAN_TYPE" = "network" ]; then
    # Network scan: needs docker socket for docker-bench
    if docker-compose -f "$DOCKER_COMPOSE_FILE" --project-directory "$DOCKER_COMPOSE_CONTEXT" run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        scanner /SimpleSecCheck/bin/security-check.sh; then
        log_success "Network security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_warning "Network security scan completed with warnings"
        OVERALL_SUCCESS=false
    fi
elif [ "$SCAN_TYPE" = "code" ]; then
    TARGET_MOUNT_PATH="$TARGET_PATH"
    TEMP_TRACKED_SNAPSHOT_DIR=""

    # CI-friendly mode: scan only git-tracked files to avoid local artifact noise.
    if [ "$SCAN_SCOPE" = "tracked" ]; then
        if git -C "$TARGET_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            TEMP_TRACKED_SNAPSHOT_DIR="$(mktemp -d /tmp/simpleseccheck-tracked-XXXXXX)"
            git -C "$TARGET_PATH" archive --format=tar HEAD | tar -xf - -C "$TEMP_TRACKED_SNAPSHOT_DIR"
            TARGET_MOUNT_PATH="$TEMP_TRACKED_SNAPSHOT_DIR"
            log_message "Using tracked-only snapshot for scan input: $TARGET_MOUNT_PATH"
        else
            log_warning "SCAN_SCOPE=tracked requested, but target is not a git repository. Falling back to full scan scope."
        fi
    fi

    # Finding policy resolution priority:
    # 1) Explicit --finding-policy
    # 2) Autodetect in target repo
    # 3) Scanner default in container (handled by security-check.sh)
    if [ -n "$FINDING_POLICY_ARG" ]; then
        if [[ "$FINDING_POLICY_ARG" = /target/* ]]; then
            FINDING_POLICY_FILE_IN_CONTAINER="$FINDING_POLICY_ARG"
        elif [[ "$FINDING_POLICY_ARG" = /* ]]; then
            # Absolute host path: only valid if it's inside the mounted target path.
            if [[ "$FINDING_POLICY_ARG" == "$TARGET_MOUNT_PATH"* ]] && [ -f "$FINDING_POLICY_ARG" ]; then
                FINDING_POLICY_FILE_IN_CONTAINER="/target${FINDING_POLICY_ARG#$TARGET_MOUNT_PATH}"
            else
                log_warning "--finding-policy absolute path is outside mounted target or does not exist. Falling back to autodetect/default."
            fi
        else
            if [ -f "$TARGET_MOUNT_PATH/$FINDING_POLICY_ARG" ]; then
                FINDING_POLICY_FILE_IN_CONTAINER="/target/$FINDING_POLICY_ARG"
            elif [ "$TARGET_MOUNT_PATH" != "$TARGET_PATH" ] && [ -f "$TARGET_PATH/$FINDING_POLICY_ARG" ]; then
                # SCAN_SCOPE=tracked uses a git snapshot; explicitly requested policy files may be untracked.
                # Copy the policy into the snapshot so explicit user input still works.
                mkdir -p "$(dirname "$TARGET_MOUNT_PATH/$FINDING_POLICY_ARG")"
                cp "$TARGET_PATH/$FINDING_POLICY_ARG" "$TARGET_MOUNT_PATH/$FINDING_POLICY_ARG"
                FINDING_POLICY_FILE_IN_CONTAINER="/target/$FINDING_POLICY_ARG"
                log_message "Copied explicit finding policy into tracked snapshot: $FINDING_POLICY_FILE_IN_CONTAINER"
            else
                log_warning "--finding-policy file not found in target: $FINDING_POLICY_ARG. Falling back to autodetect/default."
            fi
        fi
    fi

    if [ -z "$FINDING_POLICY_FILE_IN_CONTAINER" ]; then
        for policy_candidate in \
            "config/finding-policy.json" \
            "config/finding_policy.json" \
            "config/policy/finding-policy.json" \
            "config/policy/finding_policy.json" \
            "security/finding-policy.json" \
            "security/finding_policy.json" \
            ".security/finding-policy.json" \
            ".security/finding_policy.json"; do
            if [ -f "$TARGET_MOUNT_PATH/$policy_candidate" ]; then
                FINDING_POLICY_FILE_IN_CONTAINER="/target/$policy_candidate"
                log_message "Auto-detected finding policy: $FINDING_POLICY_FILE_IN_CONTAINER"
                break
            fi
        done
    fi

    if [ -n "$FINDING_POLICY_FILE_IN_CONTAINER" ]; then
        log_message "Using finding policy: $FINDING_POLICY_FILE_IN_CONTAINER"
    fi

    # Code scan: mount code directory
    # If running in container (e.g., WebUI), use /project as build context
    # Otherwise use SCRIPT_DIR (host execution)
    if [ -d "/project" ] && [ -f "/project/docker-compose.yml" ]; then
        # Running in container: use /project as build context
        DOCKER_COMPOSE_FILE="/project/docker-compose.yml"
        DOCKER_COMPOSE_CONTEXT="/project"
    else
        # Running on host: use SCRIPT_DIR
        DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
        DOCKER_COMPOSE_CONTEXT="$SCRIPT_DIR"
    fi
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" --project-directory "$DOCKER_COMPOSE_CONTEXT" run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -e SIMPLESECCHECK_EXCLUDE_PATHS="$SIMPLESECCHECK_EXCLUDE_PATHS" \
        -e FINDING_POLICY_FILE="$FINDING_POLICY_FILE_IN_CONTAINER" \
        -v "$TARGET_MOUNT_PATH:/target:ro" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
        scanner /SimpleSecCheck/bin/security-check.sh; then
        log_success "Code security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_warning "Code security scan completed with warnings"
        OVERALL_SUCCESS=false
    fi

    if [ -n "$TEMP_TRACKED_SNAPSHOT_DIR" ] && [ -d "$TEMP_TRACKED_SNAPSHOT_DIR" ]; then
        rm -rf "$TEMP_TRACKED_SNAPSHOT_DIR"
    fi
else
    # Website scan: no code mount needed
    if docker-compose -f "$DOCKER_COMPOSE_FILE" --project-directory "$DOCKER_COMPOSE_CONTEXT" run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
        scanner /SimpleSecCheck/bin/security-check.sh; then
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
