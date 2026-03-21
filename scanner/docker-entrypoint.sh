#!/bin/bash
# Don't use set -e here - we want to continue even if some setup steps fail
# The actual command execution will handle its own errors
set +e

# =========================
# 1️⃣ UID/GID Mapping - Automatically detect from PUID/PGID environment variables or /project mount
# Worker passes PUID/PGID to scanner containers via environment (from container_spec.py)
# If not set, automatically detect from /project mount (from docker-compose: .:/project:ro)
# If /project not available, uses default scanner user (1000:1000)
# =========================

SCANNER_UID=""
SCANNER_GID=""

# Check if PUID/PGID are explicitly set (passed from worker)
if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    SCANNER_UID=$PUID
    SCANNER_GID=$PGID
    echo "[Entrypoint] Using PUID=$SCANNER_UID PGID=$SCANNER_GID from environment"
elif [ -d "/project" ]; then
    # Auto-detect from /project mount (same logic as worker entrypoint)
    DETECTED_UID=$(stat -c "%u" "/project" 2>/dev/null || echo "")
    DETECTED_GID=$(stat -c "%g" "/project" 2>/dev/null || echo "")
    if [ -n "$DETECTED_UID" ] && [ -n "$DETECTED_GID" ]; then
        SCANNER_UID=$DETECTED_UID
        SCANNER_GID=$DETECTED_GID
        echo "[Entrypoint] Auto-detected UID=$SCANNER_UID GID=$SCANNER_GID from /project mount"
    else
        echo "[Entrypoint] Could not detect UID/GID from /project, using default scanner user"
    fi
else
    # No PUID/PGID set and /project not mounted - use default scanner user (1000:1000)
    echo "[Entrypoint] PUID/PGID not set and /project not mounted, using default scanner user (UID/GID from image)"
fi

# Remap scanner user if UID/GID were detected
if [ -n "$SCANNER_UID" ] && [ -n "$SCANNER_GID" ]; then
    CURRENT_UID=$(id -u scanner)
    CURRENT_GID=$(id -g scanner)
    
    # Only remap if different
    if [ "$SCANNER_GID" != "$CURRENT_GID" ]; then
        if getent group "$SCANNER_GID" >/dev/null 2>&1; then
            usermod -g "$SCANNER_GID" scanner
        else
            groupmod -g "$SCANNER_GID" scanner
        fi
    fi

    if [ "$SCANNER_UID" != "$CURRENT_UID" ]; then
        usermod -u "$SCANNER_UID" scanner
    fi
fi

# Get final UID/GID after remapping (if any)
FINAL_UID=$(id -u scanner)
FINAL_GID=$(id -g scanner)

# =========================
# 3️⃣ Ensure Results Directory and Other Volumes
# =========================
# CRITICAL: Do NOT create /app/results/logs directly!
# Each scan creates its own /app/results/{scan_id}/logs/ directory
# The results directory should only contain {scan_id}/ folders, nothing else!
# Preserve RESULTS_DIR if already set (e.g. by orchestrator when invoking report script)
RESULTS_DIR="${RESULTS_DIR:-${RESULTS_DIR_IN_CONTAINER:-/app/results}}"
export RESULTS_DIR
TARGET_DIR="${TARGET_PATH_IN_CONTAINER:-/target}"
HOME_DIR="${HOME:-/tmp/scanner}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME_DIR/.cache}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME_DIR/.config}"

mkdir -p "$HOME_DIR" "$CACHE_DIR" "$CONFIG_DIR" "$RESULTS_DIR" || true

# Set ownership once with final UID/GID
chown -R "$FINAL_UID:$FINAL_GID" "$RESULTS_DIR" "$HOME_DIR" "$CACHE_DIR" "$CONFIG_DIR" 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" "$HOME_DIR" "$CACHE_DIR" "$CONFIG_DIR" 2>/dev/null || true

# Plugin trees are chown'd to scanner:scanner at image build (e.g. UID 1000). After usermod,
# the scanner account may be a different UID (PUID/PGID / /project); files on disk keep the old
# numeric owner, so Trivy and other plugins cannot mkdir under .../plugins/.../data.
if [ -d /app/scanner/plugins ]; then
    chown -R "$FINAL_UID:$FINAL_GID" /app/scanner/plugins 2>/dev/null || true
    chmod -R u+rwX,g+rwX /app/scanner/plugins 2>/dev/null || true
fi

# Verify write access (only warn if actually not writable)
if ! gosu scanner test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR not writable by scanner (uid=$FINAL_UID gid=$FINAL_GID)"
    ls -ld "$RESULTS_DIR" || true
fi

# /target is optional - only warn if command actually needs it (not for --list)
# Check if command is --list (scanner discovery) - then /target is not needed
NEEDS_TARGET=true
for arg in "$@"; do
    if [ "$arg" = "--list" ] || [ "$arg" = "-l" ] || [ "$arg" = "--bootstrap-assets" ]; then
        NEEDS_TARGET=false
        break
    fi
done

if [ "$NEEDS_TARGET" = true ] && ! test -d "$TARGET_DIR"; then
    echo "[Entrypoint] Auto-creating $TARGET_DIR (not mounted)"
    mkdir -p "$TARGET_DIR" || true
    chown -R "$FINAL_UID:$FINAL_GID" "$TARGET_DIR" 2>/dev/null || true
    chmod -R u+rwX,g+rwX "$TARGET_DIR" 2>/dev/null || true
fi


# =========================
# Switch to scanner user and execute the command
# =========================
# Entrypoint runs as root to configure permissions and Docker group
# Now drop privileges to scanner user using gosu (standard pattern)
# This is the secure way: root setup, then non-root execution
exec gosu scanner "$@"
