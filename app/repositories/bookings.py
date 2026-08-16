from uuid import uuid4


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._bookings: list[dict[str, str | None]] = []

    def list(self) -> list[dict[str, str | None]]:
        return self._bookings

    def add(
        self,
        customer_name: str,
        service: str,
        slot: str,
        employee_id: str | None = None,
    ) -> dict[str, str | None]:
        booking = {
            "id": str(uuid4()),
            "customer_name": customer_name,
            "service": service,
            "slot": slot,
            "employee_id": employee_id,
            "status": "confirmed",
        }
        self._bookings.append(booking)
        return booking

    def cancel(self, booking_id: str) -> dict[str, str | None]:
        booking = self.get(booking_id)
        booking["status"] = "cancelled"
        return booking

    def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]:
        booking = self.get(booking_id)
        booking["slot"] = slot
        return booking

    def get(self, booking_id: str) -> dict[str, str | None]:
        for booking in self._bookings:
            if booking["id"] == booking_id:
                return booking
        raise KeyError(booking_id)


_repository = InMemoryBookingRepository()


def get_booking_repository() -> InMemoryBookingRepository:
    return _repository
