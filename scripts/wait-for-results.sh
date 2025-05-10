#!/bin/bash
set -e

RESULT_FILE="/results/security-summary.html"
TIMEOUT=300  # 5 minutes max

echo "Waiting for $RESULT_FILE to exist..."
for i in $(seq 1 $TIMEOUT); do
  if [ -f "$RESULT_FILE" ]; then
    echo "Found $RESULT_FILE, starting web server."
    exec python3 web/app.py
  fi
  sleep 1
done

echo "Timeout waiting for $RESULT_FILE"
exit 1 