"""Repository for Booking entity."""

from typing import List
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Booking
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    """Repository for Booking entity with join queries."""

    def __init__(self, session: AsyncSession):
        """Initialize BookingRepository."""
        super().__init__(session, Booking)

    async def get_by_service_id(self, service_id: str) -> List[Booking]:
        """
        Get all bookings for a service.

        Args:
            service_id: ID of the service

        Returns:
            List of Booking entities, ordered by start time
        """
        stmt = (
            select(Booking)
            .where(Booking.service_id == service_id)
            .order_by(Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_employee_id(self, employee_id: str) -> List[Booking]:
        """
        Get all bookings assigned to an employee.

        Args:
            employee_id: ID of the employee

        Returns:
            List of Booking entities, ordered by start time
        """
        stmt = (
            select(Booking)
            .where(Booking.employee_id == employee_id)
            .order_by(Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(self, status: str) -> List[Booking]:
        """
        Get all bookings with a specific status.

        Args:
            status: Status to filter by (e.g., 'pending', 'confirmed', 'cancelled')

        Returns:
            List of Booking entities, ordered by start time
        """
        stmt = (
            select(Booking)
            .where(Booking.status == status)
            .order_by(Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


# In-memory repository used by the existing (non-DB-backed) routers.
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
