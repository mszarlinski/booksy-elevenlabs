from fastapi.testclient import TestClient

from app.main import app
from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository

client = TestClient(app)


def test_search_available_slots_returns_slots_for_a_service():
    response = client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "2026-09-24"}
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] in {"emp-alice", "emp-bob"} for slot in slots)


def test_search_available_slots_filters_by_employee_id():
    response = client.get(
        "/availability",
        params={"service_id": "svc-haircut", "date": "2026-09-24", "employee_id": "emp-bob"},
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] == "emp-bob" for slot in slots)


def test_search_available_slots_excludes_an_existing_booking():
    # Uses an isolated repository (rather than the shared singleton) so this
    # test's booking doesn't leak into other test modules' assertions about
    # booking state, consistent with the override pattern used in
    # tests/test_bookings.py.
    isolated_repo = InMemoryBookingRepository()
    app.dependency_overrides[get_booking_repository] = lambda: isolated_repo
    try:
        created = client.post(
            "/bookings",
            json={
                "customer_name": "Trent",
                "service": "Men's Haircut",
                "slot": "2026-09-24T10:00",
                "confirmed": True,
                "employee_id": "emp-alice",
            },
        ).json()
        assert created["status"] == "confirmed"

        response = client.get(
            "/availability",
            params={
                "service_id": "svc-haircut",
                "date": "2026-09-24",
                "employee_id": "emp-alice",
            },
        )

        starts = {slot["start"] for slot in response.json()["slots"]}
        assert "2026-09-24T10:00" not in starts
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)


def test_search_available_slots_returns_404_for_unknown_service():
    response = client.get(
        "/availability", params={"service_id": "svc-unknown", "date": "2026-09-24"}
    )

    assert response.status_code == 404


def test_search_available_slots_returns_400_for_malformed_date():
    response = client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "not-a-date"}
    )

    assert response.status_code == 400
