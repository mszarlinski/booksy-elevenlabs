import pytest

from app.slots import generate_available_slots

SERVICE = {"id": "svc-haircut", "name": "Men's Haircut", "duration_minutes": 30, "price": 40.0}
EMPLOYEES = [
    {"id": "emp-alice", "name": "Alice", "service_ids": ["svc-haircut"]},
    {"id": "emp-bob", "name": "Bob", "service_ids": ["svc-haircut"]},
]


def test_generates_slots_within_working_hours():
    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=[], date="2026-09-20")

    starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-09-20T09:00" in starts
    assert "2026-09-20T16:30" in starts
    assert "2026-09-20T17:00" not in starts


def test_excludes_slot_that_would_run_past_closing_time():
    long_service = {**SERVICE, "duration_minutes": 45}

    slots = generate_available_slots(long_service, EMPLOYEES, bookings=[], date="2026-09-20")

    starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-09-20T16:00" in starts
    assert "2026-09-20T16:30" not in starts


def test_excludes_slots_with_existing_confirmed_booking_for_that_employee():
    bookings = [{"employee_id": "emp-alice", "slot": "2026-09-20T10:00", "status": "confirmed"}]

    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=bookings, date="2026-09-20")

    alice_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    bob_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-bob"}
    assert "2026-09-20T10:00" not in alice_starts
    assert "2026-09-20T10:00" in bob_starts


def test_ignores_cancelled_bookings():
    bookings = [{"employee_id": "emp-alice", "slot": "2026-09-20T10:00", "status": "cancelled"}]

    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=bookings, date="2026-09-20")

    alice_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-09-20T10:00" in alice_starts


def test_filters_by_earliest_and_latest_time():
    slots = generate_available_slots(
        SERVICE,
        EMPLOYEES,
        bookings=[],
        date="2026-09-20",
        earliest_time="14:00",
        latest_time="15:00",
    )

    starts = sorted({slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"})
    assert starts == ["2026-09-20T14:00", "2026-09-20T14:30", "2026-09-20T15:00"]


def test_filters_by_employee_id():
    slots = generate_available_slots(
        SERVICE, EMPLOYEES, bookings=[], date="2026-09-20", employee_id="emp-bob"
    )

    assert len(slots) > 0
    assert all(slot["employee_id"] == "emp-bob" for slot in slots)


def test_excludes_employees_who_do_not_perform_the_service():
    other_service = {"id": "svc-manicure", "name": "Manicure", "duration_minutes": 30, "price": 35.0}

    slots = generate_available_slots(other_service, EMPLOYEES, bookings=[], date="2026-09-20")

    assert slots == []


def test_raises_value_error_for_malformed_date():
    with pytest.raises(ValueError):
        generate_available_slots(SERVICE, EMPLOYEES, bookings=[], date="not-a-date")


def test_raises_value_error_for_malformed_time():
    with pytest.raises(ValueError):
        generate_available_slots(
            SERVICE, EMPLOYEES, bookings=[], date="2026-09-20", earliest_time="not-a-time"
        )


def test_raises_value_error_for_time_with_seconds():
    with pytest.raises(ValueError):
        generate_available_slots(
            SERVICE, EMPLOYEES, bookings=[], date="2026-09-20", earliest_time="09:00:00"
        )


def test_raises_value_error_for_time_with_utc_offset():
    with pytest.raises(ValueError):
        generate_available_slots(
            SERVICE, EMPLOYEES, bookings=[], date="2026-09-20", earliest_time="09:00+00:00"
        )
