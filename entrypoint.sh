#!/bin/bash
set -e

# Fix permissions for mounted volumes at container startup
if [ -d "/SimpleSecCheck/results" ]; then
    sudo chown -R scanner:scanner /SimpleSecCheck/results
fi
if [ -d "/SimpleSecCheck/logs" ]; then
    sudo chown -R scanner:scanner /SimpleSecCheck/logs
fi

# Run the command passed as arguments
exec "$@"

