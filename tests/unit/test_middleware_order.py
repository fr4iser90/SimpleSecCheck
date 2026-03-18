"""
Unit Tests: Middleware Order
Tests that middleware is registered in the correct order.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from api.main import app


def test_middleware_order():
    """
    Test that middleware is registered in the correct order:
    FastAPI adds middleware in reverse order, so the execution order is:
    1. AuthMiddleware (first - security)
    2. SecurityHeadersMiddleware (security)
    3. LoggingMiddleware (observability)
    4. CORSMiddleware (security)
    5. TrustedHostMiddleware (last - security)
    """
    # Get the middleware stack
    middleware_stack = app.user_middleware

    # Check that we have the expected number of middleware
    assert len(middleware_stack) >= 5, f"Expected at least 5 middleware, got {len(middleware_stack)}"

    # Extract middleware types
    middleware_types = [middleware.cls.__name__ for middleware in middleware_stack]

    print(f"Registered middleware: {middleware_types}")

    # Find the positions of our key middleware
    trusted_host_pos = None
    cors_pos = None
    logging_pos = None
    security_pos = None
    auth_pos = None

    for i, middleware_type in enumerate(middleware_types):
        if 'TrustedHostMiddleware' in middleware_type:
            trusted_host_pos = i
        elif 'CORSMiddleware' in middleware_type:
            cors_pos = i
        elif 'LoggingMiddleware' in middleware_type:
            logging_pos = i
        elif 'SecurityHeadersMiddleware' in middleware_type:
            security_pos = i
        elif 'AuthMiddleware' in middleware_type:
            auth_pos = i

    # Verify all middleware are present
    assert trusted_host_pos is not None, "TrustedHostMiddleware not found in middleware stack"
    assert cors_pos is not None, "CORSMiddleware not found in middleware stack"
    assert logging_pos is not None, "LoggingMiddleware not found in middleware stack"
    assert security_pos is not None, "SecurityHeadersMiddleware not found in middleware stack"
    assert auth_pos is not None, "AuthMiddleware not found in middleware stack"

    # Verify correct order (Auth first, TrustedHost last - due to FastAPI's reverse order)
    assert auth_pos < security_pos, "AuthMiddleware should come before SecurityHeadersMiddleware"
    assert security_pos < logging_pos, "SecurityHeadersMiddleware should come before LoggingMiddleware"
    assert logging_pos < cors_pos, "LoggingMiddleware should come before CORSMiddleware"
    assert cors_pos < trusted_host_pos, "CORSMiddleware should come before TrustedHostMiddleware"
    
    print("✓ Middleware order is correct")


def test_no_duplicate_security_headers():
    """
    Test that SecurityHeadersMiddleware is not duplicated.
    """
    middleware_types = [middleware.cls.__name__ for middleware in app.user_middleware]
    
    security_headers_count = sum(1 for m in middleware_types if 'SecurityHeadersMiddleware' in m)
    
    assert security_headers_count == 1, f"Expected exactly 1 SecurityHeadersMiddleware, found {security_headers_count}"
    
    print("✓ SecurityHeadersMiddleware is not duplicated")


def test_no_data_sanitization_middleware():
    """
    Test that DataSanitizationMiddleware has been removed.
    """
    middleware_types = [middleware.cls.__name__ for middleware in app.user_middleware]
    
    data_sanitization_count = sum(1 for m in middleware_types if 'DataSanitizationMiddleware' in m)
    
    assert data_sanitization_count == 0, f"DataSanitizationMiddleware should not be present, found {data_sanitization_count}"
    
    print("✓ DataSanitizationMiddleware has been removed")


def test_no_output_validation_middleware():
    """
    Test that OutputValidationMiddleware has been removed.
    """
    middleware_types = [middleware.cls.__name__ for middleware in app.user_middleware]
    
    output_validation_count = sum(1 for m in middleware_types if 'OutputValidationMiddleware' in m)
    
    assert output_validation_count == 0, f"OutputValidationMiddleware should not be present, found {output_validation_count}"
    
    print("✓ OutputValidationMiddleware has been removed")


def test_health_endpoint_accessible():
    """
    Test that the health endpoint is accessible without authentication.
    """
    client = TestClient(app)
    
    response = client.get("/api/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    print("✓ Health endpoint is accessible")


def test_metrics_endpoint_accessible():
    """
    Test that the metrics endpoint is accessible without authentication.
    """
    client = TestClient(app)
    
    response = client.get("/metrics")
    
    # Metrics endpoint should return 200 in development mode
    # Some stacks require auth here; tests expect 200
    assert response.status_code == 200
    
    # Response should contain Prometheus metrics format
    content = response.text
    assert "# HELP" in content or "# TYPE" in content, "Response should contain Prometheus metrics format"
    
    print("✓ Metrics endpoint is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])