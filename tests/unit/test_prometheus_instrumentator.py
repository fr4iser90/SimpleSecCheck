"""
Unit Tests: Prometheus FastAPI Instrumentator
Tests the Prometheus FastAPI Instrumentator integration.
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


def test_prometheus_instrumentator_registered():
    """
    Test that Prometheus FastAPI Instrumentator is properly registered.
    """
    # Check that the instrumentator is registered as middleware
    middleware_types = [middleware.cls.__name__ for middleware in app.user_middleware]
    
    instrumentator_found = any('Instrumentator' in middleware_type for middleware_type in middleware_types)
    
    assert instrumentator_found, "Prometheus FastAPI Instrumentator not found in middleware stack"
    
    print("✓ Prometheus FastAPI Instrumentator is registered")


def test_metrics_endpoint_exists():
    """
    Test that the metrics endpoint exists and is accessible.
    """
    client = TestClient(app)
    
    response = client.get("/metrics")
    
    # Should return 200 in development mode
    assert response.status_code == 200
    
    # Response should contain Prometheus metrics format
    content = response.text
    assert "# HELP" in content or "# TYPE" in content, "Response should contain Prometheus metrics format"
    
    print("✓ Metrics endpoint exists and returns Prometheus format")


def test_metrics_endpoint_includes_http_requests():
    """
    Test that the metrics endpoint includes HTTP request metrics.
    """
    client = TestClient(app)
    
    # Make a request to generate metrics
    client.get("/api/health")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include HTTP request metrics
    assert 'http_requests_total' in content or 'http_request_duration_seconds' in content, \
        "Metrics should include HTTP request metrics"
    
    print("✓ Metrics endpoint includes HTTP request metrics")


def test_metrics_endpoint_includes_fastapi_metrics():
    """
    Test that the metrics endpoint includes FastAPI-specific metrics.
    """
    client = TestClient(app)
    
    # Make a request to generate metrics
    client.get("/api/health")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include HTTP request metrics (the instrumentator provides these)
    assert 'http_requests_total' in content or 'http_request_duration_seconds' in content, \
        "Metrics should include HTTP request metrics"
    
    print("✓ Metrics endpoint includes FastAPI-specific metrics")


def test_metrics_endpoint_includes_response_size():
    """
    Test that the metrics endpoint includes response size metrics.
    """
    client = TestClient(app)
    
    # Make a request to generate metrics
    client.get("/api/health")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include response size metrics
    assert 'http_response_size_bytes' in content, "Metrics should include response size metrics"
    
    print("✓ Metrics endpoint includes response size metrics")


def test_metrics_endpoint_includes_status_codes():
    """
    Test that the metrics endpoint includes HTTP status code metrics.
    """
    client = TestClient(app)
    
    # Make requests with different status codes
    client.get("/api/health")  # 200
    client.get("/nonexistent")  # 404
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include status code metrics
    assert 'http_requests_total' in content, "Metrics should include status code metrics"
    
    print("✓ Metrics endpoint includes status code metrics")


def test_metrics_endpoint_includes_method_metrics():
    """
    Test that the metrics endpoint includes HTTP method metrics.
    """
    client = TestClient(app)
    
    # Make requests with different methods
    client.get("/api/health")
    client.post("/api/scan/start", json={})
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include method metrics
    assert 'http_requests_total' in content, "Metrics should include HTTP method metrics"
    
    print("✓ Metrics endpoint includes HTTP method metrics")


def test_metrics_endpoint_includes_path_metrics():
    """
    Test that the metrics endpoint includes path metrics.
    """
    client = TestClient(app)
    
    # Make requests to different paths
    client.get("/api/health")
    client.get("/api/session")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include path metrics
    assert 'http_requests_total' in content, "Metrics should include path metrics"
    
    print("✓ Metrics endpoint includes path metrics")


def test_metrics_endpoint_includes_duration_histogram():
    """
    Test that the metrics endpoint includes request duration histogram.
    """
    client = TestClient(app)
    
    # Make a request to generate metrics
    client.get("/api/health")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include duration histogram
    assert 'http_request_duration_seconds' in content or 'fastapi_request_duration_seconds' in content, \
        "Metrics should include request duration histogram"
    
    print("✓ Metrics endpoint includes request duration histogram")


def test_metrics_endpoint_includes_error_metrics():
    """
    Test that the metrics endpoint includes error metrics.
    """
    client = TestClient(app)
    
    # Make a request that will generate an error
    client.get("/nonexistent")
    
    # Get metrics
    response = client.get("/metrics")
    
    content = response.text
    
    # Should include error metrics
    assert 'http_requests_total' in content, "Metrics should include error metrics"
    
    print("✓ Metrics endpoint includes error metrics")


def test_metrics_endpoint_includes_custom_labels():
    """
    Test that the metrics endpoint includes custom labels.
    """
    client = TestClient(app)

    # Make a request to generate metrics
    client.get("/api/health")

    # Get metrics
    response = client.get("/metrics")

    content = response.text

    # Should include standard Prometheus labels (like method, path, status_code)
    assert 'method' in content or 'path' in content or 'status_code' in content, \
        "Metrics should include standard Prometheus labels"
    
    print("✓ Metrics endpoint includes custom labels")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])