from datetime import date as date_cls, datetime, time, timedelta

WORKDAY_START = time(9, 0)
WORKDAY_END = time(17, 0)
SLOT_INTERVAL_MINUTES = 30
TIME_FORMAT = "%H:%M"


def _parse_date(value: str) -> date_cls:
    try:
        return date_cls.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid date: {value!r}, expected YYYY-MM-DD") from exc


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, TIME_FORMAT).time()
    except ValueError as exc:
        raise ValueError(f"invalid time: {value!r}, expected HH:MM") from exc


def _eligible_employees(
    service: dict[str, str | int | float],
    employees: list[dict[str, str | list[str]]],
    employee_id: str | None,
) -> list[dict[str, str | list[str]]]:
    candidates = [employee for employee in employees if service["id"] in employee["service_ids"]]
    if employee_id is not None:
        candidates = [employee for employee in candidates if employee["id"] == employee_id]
    return candidates


def _booked_slot_keys(bookings: list[dict[str, str | None]]) -> set[tuple[str | None, str]]:
    return {
        (booking.get("employee_id"), booking["slot"])
        for booking in bookings
        if booking["status"] == "confirmed"
    }


def _slots_for_employee(
    employee: dict[str, str | list[str]],
    duration: timedelta,
    day_start: datetime,
    day_end: datetime,
    earliest: time,
    latest: time,
    booked: set[tuple[str | None, str]],
) -> list[dict[str, str]]:
    slots = []
    current = day_start
    while current + duration <= day_end:
        start_time = current.time()
        if earliest <= start_time <= latest:
            key = (employee["id"], current.isoformat(timespec="minutes"))
            if key not in booked:
                slots.append(
                    {
                        "employee_id": employee["id"],
                        "employee_name": employee["name"],
                        "start": current.isoformat(timespec="minutes"),
                        "end": (current + duration).isoformat(timespec="minutes"),
                    }
                )
        current += timedelta(minutes=SLOT_INTERVAL_MINUTES)
    return slots


def generate_available_slots(
    service: dict[str, str | int | float],
    employees: list[dict[str, str | list[str]]],
    bookings: list[dict[str, str | None]],
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
) -> list[dict[str, str]]:
    search_date = _parse_date(date)
    earliest = _parse_time(earliest_time) if earliest_time else WORKDAY_START
    latest = _parse_time(latest_time) if latest_time else WORKDAY_END

    duration = timedelta(minutes=service["duration_minutes"])
    candidates = _eligible_employees(service, employees, employee_id)
    booked = _booked_slot_keys(bookings)

    day_start = datetime.combine(search_date, WORKDAY_START)
    day_end = datetime.combine(search_date, WORKDAY_END)

    slots = []
    for employee in candidates:
        slots.extend(
            _slots_for_employee(employee, duration, day_start, day_end, earliest, latest, booked)
        )
    return slots
