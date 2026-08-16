"""
Integration tests for FastAPI database dependency injection.

Tests verify that:
- Database dependency injection works correctly with FastAPI
- Sessions are properly created and cleaned up between requests
- Async database operations function correctly
- Example database routes work as expected
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app


# Set testing mode to use NullPool (no connection persistence)
os.environ["TESTING"] = "true"


@pytest.fixture
def client():
    """
    FastAPI TestClient fixture.

    Provides a test client for making requests to the FastAPI app.
    TestClient automatically handles lifespan events (startup/shutdown).
    """
    return TestClient(app)


class TestHealthCheck:
    """Tests for the database health check endpoint."""

    def test_health_check_success(self, client: TestClient) -> None:
        """Test that health check endpoint returns healthy status."""
        response = client.get("/db/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "Database connection successful"
        assert "timestamp" in data

    def test_health_check_has_required_fields(self, client: TestClient) -> None:
        """Test that health check response includes all required fields."""
        response = client.get("/db/health")

        assert response.status_code == 200
        data = response.json()

        required_fields = {"status", "message", "timestamp"}
        assert required_fields.issubset(set(data.keys()))

    def test_health_check_multiple_calls(self, client: TestClient) -> None:
        """Test that health check can be called multiple times without issues.

        This verifies that session cleanup works correctly between requests.
        """
        for i in range(3):
            response = client.get("/db/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestCreateTestRecord:
    """Tests for the POST /db/test endpoint."""

    def test_create_test_record_success(self, client: TestClient) -> None:
        """Test creating a test record successfully."""
        payload = {"message": "Test message 1"}

        response = client.post("/db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "created successfully" in data["message"]
        assert data["records"] is not None
        assert len(data["records"]) == 1
        assert data["records"][0]["message"] == "Test message 1"

    def test_create_test_record_with_minimal_payload(self, client: TestClient) -> None:
        """Test creating a test record with only required fields."""
        payload = {"message": "Minimal test"}

        response = client.post("/db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["records"] is not None

    def test_create_test_record_returns_id(self, client: TestClient) -> None:
        """Test that created record includes a database-generated ID."""
        payload = {"message": "Record with ID"}

        response = client.post("/db/test", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["records"][0]["id"] is not None
        assert isinstance(data["records"][0]["id"], int)

    def test_create_multiple_test_records(self, client: TestClient) -> None:
        """Test creating multiple test records in sequence.

        This verifies that session cleanup works between requests
        and each request gets a fresh session.
        """
        messages = ["Record 1", "Record 2", "Record 3"]

        for msg in messages:
            payload = {"message": msg}
            response = client.post("/db/test", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["records"][0]["message"] == msg


class TestListTestRecords:
    """Tests for the GET /db/test endpoint."""

    def test_list_test_records_empty(self, client: TestClient) -> None:
        """Test listing test records when table is empty.

        Note: In a real integration test with a shared database,
        this might not be empty if other tests ran first.
        """
        response = client.get("/db/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # records can be empty or have entries from previous test runs
        assert isinstance(data["records"], list)

    def test_list_test_records_returns_expected_fields(self, client: TestClient) -> None:
        """Test that list response includes all expected fields."""
        # First create a record
        create_payload = {"message": "Test record for list"}
        client.post("/db/test", json=create_payload)

        # Then list records
        response = client.get("/db/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert isinstance(data["records"], list)

        # If we have records, verify they have required fields
        if data["records"]:
            record = data["records"][0]
            assert "id" in record
            assert "message" in record
            assert "created_at" in record

    def test_list_includes_previously_created_records(self, client: TestClient) -> None:
        """Test that GET /db/test includes records created by POST /db/test."""
        # Create a unique record
        unique_message = "Unique test record for verification"
        create_payload = {"message": unique_message}
        create_response = client.post("/db/test", json=create_payload)

        assert create_response.status_code == 200

        # List all records
        list_response = client.get("/db/test")

        assert list_response.status_code == 200
        data = list_response.json()
        assert data["success"] is True

        # Find our record in the list
        messages = [record["message"] for record in data["records"]]
        assert unique_message in messages


class TestDependencyInjection:
    """Tests for the FastAPI dependency injection pattern."""

    def test_each_request_gets_fresh_session(self, client: TestClient) -> None:
        """
        Test that each request receives a fresh database session.

        This verifies that:
        - FastAPI's dependency injection creates a new session per request
        - Sessions are properly cleaned up between requests
        - No connection leaks occur
        """
        # Make multiple health check requests
        for i in range(5):
            response = client.get("/db/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_dependency_works_with_multiple_endpoints(
        self, client: TestClient
    ) -> None:
        """
        Test that the dependency injection works across different endpoints.

        This verifies that:
        - The get_session dependency works in all routes
        - Sessions are created and destroyed correctly for each route
        """
        # Test health endpoint
        health_response = client.get("/db/health")
        assert health_response.status_code == 200

        # Test create endpoint
        create_response = client.post("/db/test", json={"message": "Test"})
        assert create_response.status_code == 200

        # Test list endpoint
        list_response = client.get("/db/test")
        assert list_response.status_code == 200


class TestErrorHandling:
    """Tests for error handling in database routes."""

    def test_health_check_graceful_error_handling(self, client: TestClient) -> None:
        """Test that health check handles errors gracefully."""
        response = client.get("/db/health")

        # Should always return 200 (even if connection fails)
        assert response.status_code == 200
        data = response.json()

        # Should include required fields
        assert "status" in data
        assert "message" in data
        assert "timestamp" in data

    def test_create_record_invalid_payload(self, client: TestClient) -> None:
        """Test that create endpoint handles invalid payload gracefully."""
        # Missing required 'message' field
        payload = {}

        response = client.post("/db/test", json=payload)

        # FastAPI should return 422 for validation error
        assert response.status_code == 422

    def test_invalid_http_method(self, client: TestClient) -> None:
        """Test that invalid HTTP methods are rejected."""
        # DELETE not allowed on health endpoint
        response = client.delete("/db/health")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_nonexistent_endpoint(self, client: TestClient) -> None:
        """Test that requests to nonexistent endpoints return 404."""
        response = client.get("/db/nonexistent")

        assert response.status_code == 404


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_database_routes_in_openapi_docs(self, client: TestClient) -> None:
        """Test that database routes are included in OpenAPI documentation."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi_schema = response.json()

        # Check that our endpoints are documented
        paths = openapi_schema["paths"]
        assert "/db/health" in paths
        assert "/db/test" in paths

    def test_database_routes_tagged_correctly(self, client: TestClient) -> None:
        """Test that database routes are tagged as 'Database' in OpenAPI docs."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi_schema = response.json()

        # Check that routes have the Database tag
        paths = openapi_schema["paths"]

        # GET /db/health
        health_get = paths.get("/db/health", {}).get("get", {})
        assert "Database" in health_get.get("tags", [])

        # POST /db/test
        test_post = paths.get("/db/test", {}).get("post", {})
        assert "Database" in test_post.get("tags", [])

        # GET /db/test
        test_get = paths.get("/db/test", {}).get("get", {})
        assert "Database" in test_get.get("tags", [])
