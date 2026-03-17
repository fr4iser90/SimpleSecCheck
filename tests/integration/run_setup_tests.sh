#!/bin/bash
# Quick script to run setup wizard tests

set -e

echo "🧪 SimpleSecCheck Setup Wizard Tests"
echo "===================================="
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Parse arguments
CLEANUP=false
TEST_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --test)
            TEST_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--cleanup] [--test TEST_NAME]"
            exit 1
            ;;
    esac
done

# Cleanup before if requested
if [ "$CLEANUP" = true ]; then
    echo "🧹 Cleaning up Docker Compose..."
    docker compose down -v 2>/dev/null || true
    sleep 2
fi

# Run tests
echo "🚀 Running setup wizard tests..."
echo ""

if [ -n "$TEST_NAME" ]; then
    pytest tests/integration/test_setup_wizard.py::"$TEST_NAME" -v -s ${CLEANUP:+--cleanup}
else
    pytest tests/integration/test_setup_wizard.py -v -s ${CLEANUP:+--cleanup}
fi

EXIT_CODE=$?

# Cleanup after if requested
if [ "$CLEANUP" = true ]; then
    echo ""
    echo "🧹 Cleaning up Docker Compose..."
    docker compose down -v 2>/dev/null || true
fi

exit $EXIT_CODE
