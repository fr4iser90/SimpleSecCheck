"""
Pytest configuration and shared fixtures
"""
import pytest
import os

# Set test environment variables
os.environ.setdefault("ENVIRONMENT", "dev")  # Use dev mode for tests by default


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--cleanup",
        action="store_true",
        default=False,
        help="Clean up Docker volumes after tests (docker compose down -v)"
    )
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        default=False,
        help="Skip cleanup (keep containers and volumes)"
    )
