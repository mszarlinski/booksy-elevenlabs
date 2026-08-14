from uuid import uuid4


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._bookings: list[dict[str, str]] = []

    def list(self) -> list[dict[str, str]]:
        return self._bookings

    def add(self, customer_name: str, service: str, slot: str) -> dict[str, str]:
        booking = {
            "id": str(uuid4()),
            "customer_name": customer_name,
            "service": service,
            "slot": slot,
            "status": "confirmed",
        }
        self._bookings.append(booking)
        return booking

    def cancel(self, booking_id: str) -> dict[str, str]:
        booking = self._get(booking_id)
        booking["status"] = "cancelled"
        return booking

    def reschedule(self, booking_id: str, slot: str) -> dict[str, str]:
        booking = self._get(booking_id)
        booking["slot"] = slot
        return booking

    def _get(self, booking_id: str) -> dict[str, str]:
        for booking in self._bookings:
            if booking["id"] == booking_id:
                return booking
        raise KeyError(booking_id)


_repository = InMemoryBookingRepository()


def get_booking_repository() -> InMemoryBookingRepository:
    return _repository
