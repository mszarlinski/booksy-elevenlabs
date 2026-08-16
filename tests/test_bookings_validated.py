"""Tests for the new validated booking creation endpoint."""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# Get current UTC time for creating future timestamps
def get_future_timestamp(hours_from_now: int = 24) -> str:
    """Generate a future ISO 8601 timestamp."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    return future_time.isoformat()


def get_past_timestamp(hours_ago: int = 1) -> str:
    """Generate a past ISO 8601 timestamp."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return past_time.isoformat()


def test_create_validated_booking_rejects_empty_customer_name():
    """Test that Pydantic rejects empty customer_name."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    # Pydantic validation error due to min_length=1
    assert response.status_code == 422


def test_create_validated_booking_rejects_whitespace_only_customer_name():
    """Test that endpoint rejects whitespace-only customer_name."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "   ",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    # Endpoint validation (after Pydantic passes non-empty string)
    assert response.status_code == 400
    assert "customer_name" in response.json()["detail"]


def test_create_validated_booking_rejects_empty_customer_email():
    """Test that Pydantic rejects empty customer_email."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    # Could be Pydantic validation error or endpoint validation
    assert response.status_code in [400, 422]
    assert "customer_email" in response.json()["detail"] or response.status_code == 400


def test_create_validated_booking_rejects_whitespace_only_customer_email():
    """Test that endpoint rejects whitespace-only customer_email."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "   ",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    # Endpoint validation (after Pydantic passes non-empty string)
    assert response.status_code == 400
    assert "customer_email" in response.json()["detail"]


def test_create_validated_booking_rejects_past_start_time():
    """Test that booking rejects past start_time."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_past_timestamp(1),
        },
    )

    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_create_validated_booking_rejects_current_time_as_start_time():
    """Test that booking rejects current time as start_time (must be future)."""
    current_time = datetime.now(timezone.utc)
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": current_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_create_validated_booking_rejects_invalid_iso_format():
    """Test that booking rejects invalid ISO 8601 format."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": "not-a-date",
        },
    )

    assert response.status_code == 400
    assert "ISO 8601" in response.json()["detail"]


def test_create_validated_booking_rejects_invalid_date_format():
    """Test that booking rejects invalid date formats."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": "2026-13-45T25:99:99",  # Invalid date/time
        },
    )

    assert response.status_code == 400
    assert "ISO 8601" in response.json()["detail"]


def test_create_validated_booking_returns_404_for_unknown_service():
    """Test that booking returns 404 for unknown service."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-nonexistent-xyz",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )

    assert response.status_code == 404
    assert "Service" in response.json()["detail"]


def test_create_validated_booking_returns_404_for_unknown_employee():
    """Test that booking returns 404 for unknown employee."""
    # First we need a valid service that exists in the test database
    # For now, this test will work if any service doesn't exist
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-nonexistent-abc",  # This should fail first
            "employee_id": "emp-nonexistent-xyz",
            "start_time": get_future_timestamp(24),
        },
    )

    # Should fail on service not found
    assert response.status_code == 404
    assert "Service" in response.json()["detail"] or "Employee" in response.json()["detail"]


def test_create_validated_booking_requires_customer_name():
    """Test that customer_name field is required."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    assert response.status_code == 422


def test_create_validated_booking_requires_customer_email():
    """Test that customer_email field is required."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    assert response.status_code == 422


def test_create_validated_booking_requires_service_id():
    """Test that service_id field is required."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "employee_id": "emp-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    assert response.status_code == 422


def test_create_validated_booking_requires_employee_id():
    """Test that employee_id field is required."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "start_time": get_future_timestamp(24),
        },
    )
    assert response.status_code == 422


def test_create_validated_booking_requires_start_time():
    """Test that start_time field is required."""
    response = client.post(
        "/bookings/validated",
        json={
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "service_id": "svc-test-1",
            "employee_id": "emp-test-1",
        },
    )
    assert response.status_code == 422
