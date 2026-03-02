"""
Pytest configuration and shared fixtures
"""
import pytest
import os

# Set test environment variables
os.environ.setdefault("ENVIRONMENT", "dev")  # Use dev mode for tests by default
