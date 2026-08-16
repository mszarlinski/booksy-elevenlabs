from fastapi.testclient import TestClient

from app.main import app
from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository

client = TestClient(app)


class CountingBookingRepository(InMemoryBookingRepository):
    def __init__(self) -> None:
        super().__init__()
        self.cancel_calls = 0
        self.reschedule_calls = 0

    def cancel(self, booking_id: str) -> dict[str, str]:
        self.cancel_calls += 1
        return super().cancel(booking_id)

    def reschedule(self, booking_id: str, slot: str) -> dict[str, str]:
        self.reschedule_calls += 1
        return super().reschedule(booking_id, slot)


def test_bookings_returns_200_and_empty_list():
    response = client.get("/bookings")

    assert response.status_code == 200
    assert response.json() == {"bookings": []}


def test_create_booking_returns_confirmed_booking():
    response = client.post(
        "/bookings",
        json={"customer_name": "Alice", "service": "Haircut", "slot": "2026-08-15T18:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["customer_name"] == "Alice"
    assert body["service"] == "Haircut"
    assert body["slot"] == "2026-08-15T18:00"
    assert body["status"] == "confirmed"
    assert "id" in body


def test_cancel_booking_sets_status_to_cancelled():
    created = client.post(
        "/bookings",
        json={"customer_name": "Bob", "service": "Shave", "slot": "2026-08-15T19:00"},
    ).json()

    response = client.post(f"/bookings/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_reschedule_booking_updates_slot():
    created = client.post(
        "/bookings",
        json={"customer_name": "Carol", "service": "Haircut", "slot": "2026-08-15T10:00"},
    ).json()

    response = client.post(
        f"/bookings/{created['id']}/reschedule", json={"slot": "2026-08-16T10:00"}
    )

    assert response.status_code == 200
    assert response.json()["slot"] == "2026-08-16T10:00"


def test_create_booking_is_idempotent_on_retry():
    request = {
        "customer_name": "Dana",
        "service": "Haircut",
        "slot": "2026-08-17T10:00",
    }
    headers = {"Idempotency-Key": "retry-key-1"}

    first = client.post("/bookings", json=request, headers=headers)
    second = client.post("/bookings", json=request, headers=headers)

    assert first.json() == second.json()

    bookings = client.get("/bookings").json()["bookings"]
    matching = [b for b in bookings if b["id"] == first.json()["id"]]
    assert len(matching) == 1


def test_cancel_booking_does_not_repeat_mutation_on_retry():
    counting_repo = CountingBookingRepository()
    app.dependency_overrides[get_booking_repository] = lambda: counting_repo
    try:
        created = client.post(
            "/bookings",
            json={"customer_name": "Eve", "service": "Haircut", "slot": "2026-08-18T10:00"},
        ).json()
        headers = {"Idempotency-Key": "cancel-retry-key-1"}

        client.post(f"/bookings/{created['id']}/cancel", headers=headers)
        client.post(f"/bookings/{created['id']}/cancel", headers=headers)

        assert counting_repo.cancel_calls == 1
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)


def test_create_booking_accepts_optional_employee_id():
    response = client.post(
        "/bookings",
        json={
            "customer_name": "Grace",
            "service": "Haircut",
            "slot": "2026-08-21T10:00",
            "employee_id": "emp-alice",
        },
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == "emp-alice"


def test_create_booking_without_employee_id_defaults_to_none():
    response = client.post(
        "/bookings",
        json={"customer_name": "Heidi", "service": "Haircut", "slot": "2026-08-21T11:00"},
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] is None


def test_reschedule_booking_does_not_repeat_mutation_on_retry():
    counting_repo = CountingBookingRepository()
    app.dependency_overrides[get_booking_repository] = lambda: counting_repo
    try:
        created = client.post(
            "/bookings",
            json={"customer_name": "Frank", "service": "Haircut", "slot": "2026-08-19T10:00"},
        ).json()
        headers = {"Idempotency-Key": "reschedule-retry-key-1"}
        body = {"slot": "2026-08-20T10:00"}

        client.post(f"/bookings/{created['id']}/reschedule", json=body, headers=headers)
        client.post(f"/bookings/{created['id']}/reschedule", json=body, headers=headers)

        assert counting_repo.reschedule_calls == 1
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)
