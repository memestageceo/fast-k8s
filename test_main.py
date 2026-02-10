"""
Comprehensive test suite for the FastAPI Kubernetes Inspector application.
"""
import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app, increment, is_ready


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def reset_counter():
    """Reset the global counter before each test."""
    import main
    main.counter = 0
    yield
    main.counter = 0


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_liveness_probe(self, client):
        """Test that liveness probe returns 200 OK."""
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_health_endpoint(self, client):
        """Test general health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness_probe_not_ready(self, client):
        """Test readiness probe when app is not ready."""
        with patch('main.is_ready', return_value=False):
            response = client.get("/ready")
            assert response.status_code == 503
            assert response.json() == {"status": "not ready"}

    def test_readiness_probe_ready(self, client):
        """Test readiness probe when app is ready."""
        with patch('main.is_ready', return_value=True):
            response = client.get("/ready")
            assert response.status_code == 200
            assert response.json() == {"status": "ready"}


class TestMainEndpoints:
    """Test suite for main application endpoints."""

    def test_home_page_loads(self, client, reset_counter):
        """Test that home page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"API" in response.content
        assert b"Runtime" in response.content

    def test_home_page_increments_counter(self, client, reset_counter):
        """Test that accessing home page increments counter."""
        response1 = client.get("/")
        assert response1.status_code == 200

        response2 = client.get("/")
        assert response2.status_code == 200

        # Counter should be incremented
        # We can verify this through the whoami endpoint
        whoami_response = client.get("/whoami")
        assert whoami_response.json()["count"] == 2

    def test_whoami_endpoint(self, client, reset_counter):
        """Test whoami endpoint returns correct structure."""
        response = client.get("/whoami")
        assert response.status_code == 200

        data = response.json()
        assert "pod" in data
        assert "node" in data
        assert "hostname" in data
        assert "count" in data
        assert "ready" in data

        # Counter should be 0 since we haven't accessed home page
        assert data["count"] == 0

    def test_whoami_with_mocked_pod_identity(self, client):
        """Test whoami endpoint with mocked pod identity."""
        with patch('main.POD_IDENTITY', {
            'pod': 'test-pod-123',
            'node': 'test-node-456',
            'app_env': 'test',
            'service_name': 'test-service'
        }):
            response = client.get("/whoami")
            data = response.json()

            assert data["pod"] == "test-pod-123"
            assert data["node"] == "test-node-456"


class TestCounterFunctions:
    """Test suite for counter-related functions."""

    def test_increment_function(self, reset_counter):
        """Test that increment function works correctly."""
        result1 = increment()
        assert result1 == 1

        result2 = increment()
        assert result2 == 2

        result3 = increment()
        assert result3 == 3

    def test_increment_thread_safety(self, reset_counter):
        """Test that increment is thread-safe under concurrent access."""
        num_threads = 10
        increments_per_thread = 100
        threads = []

        def worker():
            for _ in range(increments_per_thread):
                increment()

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final count is correct
        import main
        expected_count = num_threads * increments_per_thread
        assert main.counter == expected_count

    def test_is_ready_function(self):
        """Test readiness check function."""
        with patch('main.READY_AFTER', 2):
            with patch('main.START_TIME', time.time() - 3):
                # App has been running for 3 seconds, READY_AFTER is 2
                assert is_ready() is True

            with patch('main.START_TIME', time.time() - 1):
                # App has been running for 1 second, READY_AFTER is 2
                assert is_ready() is False


class TestErrorHandling:
    """Test suite for error handling."""

    def test_home_page_with_missing_template(self, client):
        """Test home page handles missing template gracefully."""
        with patch('main.templates.TemplateResponse', side_effect=Exception("Template error")):
            response = client.get("/")
            assert response.status_code == 500

    def test_whoami_with_exception(self, client):
        """Test whoami endpoint handles exceptions."""
        with patch('socket.gethostname', side_effect=Exception("Socket error")):
            response = client.get("/whoami")
            assert response.status_code == 500


class TestEnvironmentVariables:
    """Test suite for environment variable handling."""

    def test_ready_after_valid_value(self):
        """Test READY_AFTER with valid value."""
        with patch.dict('os.environ', {'READY_AFTER': '10'}):
            # Re-import to trigger environment variable parsing
            import importlib

            import main as main_module
            importlib.reload(main_module)
            assert main_module.READY_AFTER == 10

    def test_ready_after_invalid_value(self):
        """Test READY_AFTER with invalid value falls back to default."""
        with patch.dict('os.environ', {'READY_AFTER': 'invalid'}):
            import importlib

            import main as main_module
            importlib.reload(main_module)
            # Should fall back to default value
            assert main_module.READY_AFTER == 5

    def test_ready_after_negative_value(self):
        """Test READY_AFTER with negative value."""
        with patch.dict('os.environ', {'READY_AFTER': '-5'}):
            import importlib

            import main as main_module
            importlib.reload(main_module)
            # Should fall back to default value
            assert main_module.READY_AFTER == 5


class TestCORS:
    """Test suite for CORS configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/whoami",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert "access-control-allow-origin" in response.headers


class TestOpenAPIDocumentation:
    """Test suite for OpenAPI documentation."""

    def test_openapi_json_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "info" in schema
        assert schema["info"]["title"] == "FastAPI Kubernetes Inspector"

    def test_docs_page_available(self, client):
        """Test that interactive docs page is available."""
        response = client.get("/docs")
        assert response.status_code == 200
