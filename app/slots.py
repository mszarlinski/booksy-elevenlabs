from datetime import date as date_cls, datetime, time, timedelta

WORKDAY_START = time(9, 0)
WORKDAY_END = time(17, 0)
SLOT_INTERVAL_MINUTES = 30


def generate_available_slots(
    service: dict[str, str | int | float],
    employees: list[dict[str, str | list[str]]],
    bookings: list[dict[str, str | None]],
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
) -> list[dict[str, str]]:
    try:
        search_date = date_cls.fromisoformat(date)
    except ValueError as exc:
        raise ValueError(f"invalid date: {date!r}, expected YYYY-MM-DD") from exc

    try:
        earliest = time.fromisoformat(earliest_time) if earliest_time else WORKDAY_START
        latest = time.fromisoformat(latest_time) if latest_time else WORKDAY_END
    except ValueError as exc:
        raise ValueError("invalid earliest_time/latest_time, expected HH:MM") from exc

    duration = timedelta(minutes=service["duration_minutes"])

    candidates = [employee for employee in employees if service["id"] in employee["service_ids"]]
    if employee_id is not None:
        candidates = [employee for employee in candidates if employee["id"] == employee_id]

    booked = {
        (booking.get("employee_id"), booking["slot"])
        for booking in bookings
        if booking["status"] == "confirmed"
    }

    day_start = datetime.combine(search_date, WORKDAY_START)
    day_end = datetime.combine(search_date, WORKDAY_END)

    slots = []
    for employee in candidates:
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
