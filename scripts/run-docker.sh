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

# Don't exit on error immediately - we want to log errors first
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Define log_message early for debugging (write to stdout so it's captured)
# RUN_DOCKER_LOG will be set later after LOGS_DIR is determined
RUN_DOCKER_LOG="/dev/null"
log_message() {
    local msg="${BLUE}[SimpleSecCheck Docker]${NC} $1"
    echo -e "$msg"
    if [ "$RUN_DOCKER_LOG" != "/dev/null" ] && [ -n "$RUN_DOCKER_LOG" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    fi
}
log_message "Starting run-docker.sh script..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log_message "SCRIPT_DIR: $SCRIPT_DIR"
SCAN_SCOPE="${SCAN_SCOPE:-full}" # full | tracked
SIMPLESECCHECK_EXCLUDE_PATHS="${SIMPLESECCHECK_EXCLUDE_PATHS:-}"
CI_MODE=false
TARGET=""
FINDING_POLICY_ARG=""
FINDING_POLICY_FILE_IN_CONTAINER=""
COLLECT_METADATA=false

print_usage() {
    echo "Usage: $0 [--ci] [--finding-policy <path>] [--collect-metadata] <target>"
    echo ""
    echo "Examples:"
    echo "  $0 /home/user/my-project          # Scan local code"
    echo "  $0 --ci /home/user/my-project     # CI-friendly code scan"
    echo "  $0 --finding-policy config/finding-policy.json /home/user/my-project"
    echo "  $0 --collect-metadata /home/user/my-project  # Collect scan metadata (optional)"
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
        --collect-metadata)
            COLLECT_METADATA=true
            shift
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
        SIMPLESECCHECK_EXCLUDE_PATHS=".git,node_modules,dist,build,coverage,.next,.nuxt,.cache"
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

    # Check if TARGET is a temporary Git clone path (in results/tmp/)
    # If so, try to extract project name from GIT_URL environment variable or use basename
    if [[ "$TARGET" =~ results/tmp/ ]] || [[ "$TARGET" =~ ^/.*/tmp/ ]]; then
        # Temporary Git clone path - try to get repo name from GIT_URL or use basename of parent
        if [ -n "${GIT_URL:-}" ]; then
            # Extract repo name from Git URL (same logic as step_service.py)
            if [[ "$GIT_URL" =~ github\.com ]] || [[ "$GIT_URL" =~ gitlab\.com ]]; then
                PROJECT_NAME=$(echo "$GIT_URL" | sed 's|.*/||' | sed 's|\.git$||')
            else
                PROJECT_NAME=$(basename "$TARGET")
            fi
        else
            # Fallback: use basename of target (will be temp dir name, but better than nothing)
            PROJECT_NAME=$(basename "$TARGET")
        fi
    else
        # Regular local path
        PROJECT_NAME=$(basename "$TARGET")
    fi
fi

# Use SCAN_ID if provided (from WebUI), otherwise generate timestamp
if [ -n "${SCAN_ID:-}" ]; then
    TIMESTAMP="$SCAN_ID"
else
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
fi
PROJECT_DIR="${PROJECT_NAME}_${TIMESTAMP}"

# Script now only runs on host (CLI usage)
# WebUI calls docker-compose directly, so no container/host distinction needed
# Allow RESULTS_DIR to be overridden via environment variable (for production)
if [ -z "$RESULTS_DIR" ]; then
    RESULTS_DIR="$SCRIPT_DIR/results/$PROJECT_DIR"
else
    log_message "Using RESULTS_DIR from environment: '$RESULTS_DIR'"
fi
LOGS_DIR="$RESULTS_DIR/logs"
log_message "Using script dir: RESULTS_DIR='$RESULTS_DIR'"

# Store original for later reference
OVERALL_SUCCESS=false

# Functions (log_message already defined above for early logging)

log_success() {
    local msg="${GREEN}[SUCCESS]${NC} $1"
    echo -e "$msg"
    if [ -n "$RUN_DOCKER_LOG" ] && [ "$RUN_DOCKER_LOG" != "/dev/null" ] && [ -f "$RUN_DOCKER_LOG" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    fi
}

log_warning() {
    local msg="${YELLOW}[WARNING]${NC} $1"
    echo -e "$msg"
    if [ -n "$RUN_DOCKER_LOG" ] && [ "$RUN_DOCKER_LOG" != "/dev/null" ] && [ -f "$RUN_DOCKER_LOG" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    fi
}

log_error() {
    local msg="${RED}[ERROR]${NC} $1"
    echo -e "$msg" >&2
    if [ -n "$RUN_DOCKER_LOG" ] && [ "$RUN_DOCKER_LOG" != "/dev/null" ] && [ -f "$RUN_DOCKER_LOG" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    fi
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

# Create directories (only if running on host, not in container)
# When running in container, docker-compose will create directories when mounting
if [ ! -d "/project" ] || [ ! -f "/project/docker-compose.yml" ]; then
    # Running on host: create directories
    mkdir -p "$RESULTS_DIR" "$LOGS_DIR"
fi

# Create log file for run-docker.sh execution (always, even in container)
RUN_DOCKER_LOG="$LOGS_DIR/orchestrator.log"
mkdir -p "$LOGS_DIR"
touch "$RUN_DOCKER_LOG"
log_message "Logging to: $RUN_DOCKER_LOG"

echo ""
echo -e "${BLUE} SimpleSecCheck Docker Security Scanner${NC}"
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
export COLLECT_METADATA="$COLLECT_METADATA"  # Only collect metadata if explicitly enabled

# Load optional API tokens from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}[INFO]${NC} Loading API tokens from .env file..."
    set -a  # Export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # Stop automatically exporting
fi

# Script now only runs on host (CLI usage)
# WebUI calls docker-compose directly, so no container/host distinction needed
# Use docker-compose.prod.yml in production, docker-compose.yml in dev
if [ "${ENVIRONMENT:-dev}" = "prod" ]; then
    DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
else
    DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
fi
DOCKER_COMPOSE_CONTEXT="$SCRIPT_DIR"

# Script now only runs on host (CLI usage)
# WebUI calls docker-compose directly, so no container/host distinction needed
OWASP_DATA_VOLUME="-v $SCRIPT_DIR/owasp-dependency-check-data:/SimpleSecCheck/owasp-dependency-check-data"
log_message "[OWASP Volume] Using absolute path: $OWASP_DATA_VOLUME"
if [ -d "$SCRIPT_DIR/owasp-dependency-check-data" ]; then
    log_message "[OWASP Volume] ✓ Host path exists"
else
    log_warning "[OWASP Volume] ✗ Host path does NOT exist: $SCRIPT_DIR/owasp-dependency-check-data"
fi

# Run Docker Compose with the scanner service
if [ "$SCAN_TYPE" = "network" ]; then
    # Network scan: needs docker socket for docker-bench
    if docker-compose -f "$DOCKER_COMPOSE_FILE" --project-directory "$DOCKER_COMPOSE_CONTEXT" run --rm \
        -e SCAN_TYPE="$SCAN_TYPE" \
        -e ZAP_TARGET="$ZAP_TARGET" \
        -e TARGET_URL="$ZAP_TARGET" \
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR" \
        -e COLLECT_METADATA="$COLLECT_METADATA" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        scanner /SimpleSecCheck/scripts/security-check.sh; then
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
            # Check if TARGET_PATH is a temporary Git clone (from WebUI)
            # If so, use host-mounted results/tmp directory instead of /tmp
            if [[ "$TARGET_PATH" =~ results/tmp ]]; then
                # Git clone from WebUI - create snapshot in host-mounted results/tmp directory
                if [ -d "/project" ] && [ -f "/project/docker-compose.yml" ]; then
                    # Running in WebUI container: use host-mounted results directory
                    TEMP_TRACKED_SNAPSHOT_DIR="$(mktemp -d "$RESULTS_DIR/tmp/simpleseccheck-tracked-XXXXXX")"
                else
                    # Running on host: use results directory
                    TEMP_TRACKED_SNAPSHOT_DIR="$(mktemp -d "$RESULTS_DIR/tmp/simpleseccheck-tracked-XXXXXX")"
                fi
                log_message "Creating tracked snapshot in host-mounted directory: $TEMP_TRACKED_SNAPSHOT_DIR"
            else
                # Regular local path - use /tmp (will be cleaned up after scan)
                TEMP_TRACKED_SNAPSHOT_DIR="$(mktemp -d /tmp/simpleseccheck-tracked-XXXXXX)"
                log_message "Creating tracked snapshot in temporary directory: $TEMP_TRACKED_SNAPSHOT_DIR"
            fi
            
            log_message "Creating git archive from: $TARGET_PATH"
            if git -C "$TARGET_PATH" archive --format=tar HEAD | tar -xf - -C "$TEMP_TRACKED_SNAPSHOT_DIR"; then
                FILE_COUNT=$(find "$TEMP_TRACKED_SNAPSHOT_DIR" -type f 2>/dev/null | wc -l)
                log_message "Git archive created successfully with $FILE_COUNT files"
                TARGET_MOUNT_PATH="$TEMP_TRACKED_SNAPSHOT_DIR"
                log_message "Using tracked-only snapshot for scan input: $TARGET_MOUNT_PATH"
            else
                log_error "Failed to create git archive snapshot"
                log_warning "Falling back to full scan scope"
                TARGET_MOUNT_PATH="$TARGET_PATH"
            fi
            
            # If a finding policy was explicitly specified (relative path), try to copy it into the snapshot
            # (it might not be tracked in git, so it won't be in the snapshot)
            # Since git -C "$TARGET_PATH" succeeded, we can use git to access the file even if we're in a container
            if [ -n "$FINDING_POLICY_ARG" ] && [[ ! "$FINDING_POLICY_ARG" = /* ]] && [[ ! "$FINDING_POLICY_ARG" = /target/* ]]; then
                # Check if file exists in original target and is not already in snapshot
                if [ ! -f "$TEMP_TRACKED_SNAPSHOT_DIR/$FINDING_POLICY_ARG" ]; then
                    # Try to copy from original target (works on host, may fail in container)
                    if [ -f "$TARGET_PATH/$FINDING_POLICY_ARG" ]; then
                        mkdir -p "$(dirname "$TEMP_TRACKED_SNAPSHOT_DIR/$FINDING_POLICY_ARG")"
                        cp "$TARGET_PATH/$FINDING_POLICY_ARG" "$TEMP_TRACKED_SNAPSHOT_DIR/$FINDING_POLICY_ARG"
                        log_message "Copied explicit finding policy into tracked snapshot: /target/$FINDING_POLICY_ARG"
                    else
                        # File doesn't exist at TARGET_PATH (might be in container where path doesn't exist)
                        # Since git -C "$TARGET_PATH" works, try to get the git root and access file from there
                        GIT_ROOT="$(git -C "$TARGET_PATH" rev-parse --show-toplevel 2>/dev/null || echo "")"
                        if [ -n "$GIT_ROOT" ]; then
                            if [ -f "$GIT_ROOT/$FINDING_POLICY_ARG" ]; then
                                mkdir -p "$(dirname "$TEMP_TRACKED_SNAPSHOT_DIR/$FINDING_POLICY_ARG")"
                                cp "$GIT_ROOT/$FINDING_POLICY_ARG" "$TEMP_TRACKED_SNAPSHOT_DIR/$FINDING_POLICY_ARG"
                                log_message "Copied explicit finding policy into tracked snapshot from git root: /target/$FINDING_POLICY_ARG"
                            else
                                log_warning "Finding policy file not found at git root: $GIT_ROOT/$FINDING_POLICY_ARG"
                            fi
                        else
                            log_warning "Could not determine git root for target path: $TARGET_PATH"
                        fi
                    fi
                fi
            fi
        else
            log_warning "SCAN_SCOPE=tracked requested, but target is not a git repository. Falling back to full scan scope."
        fi
    fi

    # Finding policy resolution priority:
    # 1) Explicit --finding-policy (relative path: will be in /target, absolute path: must be in target)
    # 2) Autodetect in target repo (done later in security-check.sh)
    # NO DEFAULT POLICY - if not found, no policy is applied
    if [ -n "$FINDING_POLICY_ARG" ]; then
        if [[ "$FINDING_POLICY_ARG" = /target/* ]]; then
            # Already a container path
            FINDING_POLICY_FILE_IN_CONTAINER="$FINDING_POLICY_ARG"
        elif [[ "$FINDING_POLICY_ARG" = /* ]]; then
            # Absolute host path: convert to container path if inside target
            # Check if we're in a container (can't validate host paths)
            if [ -d "/app" ] || [ -f "/.dockerenv" ]; then
                # Running in container: assume path is inside target, convert to /target/...
                # Extract relative path from absolute path (assumes it's inside target)
                FINDING_POLICY_FILE_IN_CONTAINER="/target/$(basename "$FINDING_POLICY_ARG")"
                log_message "Running in container - converting absolute policy path to: $FINDING_POLICY_FILE_IN_CONTAINER"
            elif [[ "$FINDING_POLICY_ARG" == "$TARGET_MOUNT_PATH"* ]] && [ -f "$FINDING_POLICY_ARG" ]; then
                # Running on host: validate path exists and is inside target
                FINDING_POLICY_FILE_IN_CONTAINER="/target${FINDING_POLICY_ARG#$TARGET_MOUNT_PATH}"
            else
                log_warning "--finding-policy absolute path is outside mounted target or does not exist. Will attempt auto-detection in target project."
            fi
        else
            # Relative path: will be automatically available at /target/$FINDING_POLICY_ARG
            # (just like the target project itself - Docker mounts it!)
            FINDING_POLICY_FILE_IN_CONTAINER="/target/$FINDING_POLICY_ARG"
            if [ -d "/app" ] || [ -f "/.dockerenv" ]; then
                log_message "Running in container - policy will be at: $FINDING_POLICY_FILE_IN_CONTAINER (mounted with target)"
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
    # EINHEITLICH: Dev und Prod verwenden beide /project (gemountet von .:/project:ro)
    TARGET_MOUNT_PATH_HOST="$TARGET_MOUNT_PATH"
    RESULTS_DIR_HOST="$RESULTS_DIR"
    LOGS_DIR_HOST="$LOGS_DIR"
    
    # Check if we're running in a container (e.g., WebUI container at /app)
    # If so, skip path validation - docker-compose will handle it when mounting
    if [ -d "/app" ] || [ -f "/.dockerenv" ]; then
        # Running in container: cannot validate host paths, let docker-compose handle it
        log_message "Running in container - path validation will be done by docker-compose when mounting"
    else
        # Running on host: validate path exists
        if [ ! -d "$TARGET_MOUNT_PATH_HOST" ]; then
            log_error "Target path does not exist: $TARGET_MOUNT_PATH_HOST"
            log_error "Exiting with error code 1"
            exit 1
        fi
        log_message "✓ Target path exists: $TARGET_MOUNT_PATH_HOST"
        
        # Count files in target directory for debugging
        FILE_COUNT=$(find "$TARGET_MOUNT_PATH_HOST" -type f 2>/dev/null | wc -l)
        log_message "Target directory contains $FILE_COUNT files"
        
        if [ "$FILE_COUNT" -eq 0 ]; then
            log_warning "WARNING: Target directory is empty! Scanner will find nothing!"
            log_warning "Directory contents:"
            ls -la "$TARGET_MOUNT_PATH_HOST" 2>/dev/null || log_warning "  (cannot list directory)"
        fi
    fi
    
    # Build environment variables array
    DOCKER_ENV_ARGS=(
        -e SCAN_TYPE="$SCAN_TYPE"
        -e ZAP_TARGET="$ZAP_TARGET"
        -e TARGET_URL="$ZAP_TARGET"
        -e PROJECT_RESULTS_DIR="$RESULTS_DIR"
        -e SIMPLESECCHECK_EXCLUDE_PATHS="$SIMPLESECCHECK_EXCLUDE_PATHS"
        -e COLLECT_METADATA="$COLLECT_METADATA"
        -e TARGET_PATH_HOST="$TARGET_MOUNT_PATH"
    )
    
    # Only set FINDING_POLICY_FILE if a policy was found (NO DEFAULT!)
    if [ -n "$FINDING_POLICY_FILE_IN_CONTAINER" ]; then
        DOCKER_ENV_ARGS+=(-e FINDING_POLICY_FILE="$FINDING_POLICY_FILE_IN_CONTAINER")
    fi
    
    log_message "Mounting volumes:"
    log_message "  -v $TARGET_MOUNT_PATH_HOST:/target:ro"
    log_message "  -v $RESULTS_DIR_HOST:/SimpleSecCheck/results"
    log_message "  -v $LOGS_DIR_HOST:/SimpleSecCheck/logs"
    log_message "Docker Compose file: $DOCKER_COMPOSE_FILE"
    log_message "Docker Compose context: $DOCKER_COMPOSE_CONTEXT"
    
    # Execute docker-compose command and capture ALL output (stdout + stderr) to log file
    log_message "Executing docker-compose command..."
    log_message "Full command: docker-compose -f $DOCKER_COMPOSE_FILE --project-directory $DOCKER_COMPOSE_CONTEXT run --rm ..."
    
    # Capture both stdout and stderr, write to log file AND stdout
    DOCKER_COMPOSE_OUTPUT=$(docker-compose -f "$DOCKER_COMPOSE_FILE" --project-directory "$DOCKER_COMPOSE_CONTEXT" run --rm \
        "${DOCKER_ENV_ARGS[@]}" \
        -v "$TARGET_MOUNT_PATH_HOST:/target:ro" \
        -v "$RESULTS_DIR_HOST:/SimpleSecCheck/results" \
        -v "$LOGS_DIR_HOST:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
        scanner /SimpleSecCheck/scripts/security-check.sh 2>&1)
    DOCKER_EXIT_CODE=$?
    
    # Write output to log file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Docker Compose output:" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    echo "$DOCKER_COMPOSE_OUTPUT" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Docker Compose exit code: $DOCKER_EXIT_CODE" >> "$RUN_DOCKER_LOG" 2>/dev/null || true
    
    # Also output to stdout (for scan_service.py to capture)
    echo "$DOCKER_COMPOSE_OUTPUT"
    
    if [ $DOCKER_EXIT_CODE -eq 0 ]; then
        log_success "Code security scan completed successfully!"
        OVERALL_SUCCESS=true
    else
        log_error "Docker Compose command failed with exit code: $DOCKER_EXIT_CODE"
        log_error "Last 20 lines of Docker Compose output:"
        echo "$DOCKER_COMPOSE_OUTPUT" | tail -20 | while read -r line; do
            log_error "  $line"
        done
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
        -e COLLECT_METADATA="$COLLECT_METADATA" \
        -v "$RESULTS_DIR:/SimpleSecCheck/results" \
        -v "$LOGS_DIR:/SimpleSecCheck/logs" \
        $OWASP_DATA_VOLUME \
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
[ -f "$LOGS_DIR/scan.log" ] && echo -e "  ${GREEN}✓${NC} Log File: $LOGS_DIR/scan.log"

echo ""
log_message "SimpleSecCheck Docker Security Scan Completed: $(date)"
