#!/bin/bash
# Align backend UID/GID with host project owner (same pattern as worker/scanner).
set +e

BACKEND_UID=""
BACKEND_GID=""

if [ -d "/project" ]; then
    DETECTED_UID=$(stat -c "%u" "/project" 2>/dev/null || echo "")
    DETECTED_GID=$(stat -c "%g" "/project" 2>/dev/null || echo "")
    if [ -n "$DETECTED_UID" ] && [ -n "$DETECTED_GID" ]; then
        BACKEND_UID=$DETECTED_UID
        BACKEND_GID=$DETECTED_GID
        echo "[Backend Entrypoint] Auto-detected UID=$BACKEND_UID GID=$BACKEND_GID from /project mount"

        CURRENT_UID=$(id -u backend)
        CURRENT_GID=$(id -g backend)

        if [ "$BACKEND_GID" != "$CURRENT_GID" ]; then
            if getent group "$BACKEND_GID" >/dev/null 2>&1; then
                usermod -g "$BACKEND_GID" backend
            else
                groupmod -g "$BACKEND_GID" backend
            fi
        fi

        if [ "$BACKEND_UID" != "$CURRENT_UID" ]; then
            usermod -u "$BACKEND_UID" backend
        fi
    else
        echo "[Backend Entrypoint] Could not detect UID/GID from /project, using default backend user"
    fi
else
    echo "[Backend Entrypoint] /project not mounted, using default backend user"
fi

FINAL_UID=$(id -u backend)
FINAL_GID=$(id -g backend)

RESULTS_DIR="${RESULTS_DIR:-/app/results}"
UPLOADS_DIR="${UPLOAD_STORAGE_PATH:-/app/uploads}"
mkdir -p "$RESULTS_DIR" "$UPLOADS_DIR" 2>/dev/null || true

echo "[Backend Entrypoint] chown $RESULTS_DIR $UPLOADS_DIR /app to UID=$FINAL_UID GID=$FINAL_GID"
chown -R "$FINAL_UID:$FINAL_GID" "$RESULTS_DIR" "$UPLOADS_DIR" /app 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" "$UPLOADS_DIR" 2>/dev/null || true

if ! gosu backend test -w "$RESULTS_DIR" 2>/dev/null; then
    echo "[Backend Entrypoint] WARNING: $RESULTS_DIR not writable by backend (uid=$FINAL_UID)"
    ls -ld "$RESULTS_DIR" || true
fi

exec gosu backend "$@"
