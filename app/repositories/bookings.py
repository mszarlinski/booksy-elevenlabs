"""Repository for Booking entity."""

from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
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

    def _calculate_booking_end_time(self, start_time: datetime, duration_minutes: int) -> datetime:
        """
        Calculate the end time of a booking.

        Args:
            start_time: The start time of the booking
            duration_minutes: Duration of the service in minutes

        Returns:
            The calculated end time (start_time + duration_minutes)
        """
        return start_time + timedelta(minutes=duration_minutes)

    async def check_and_create_booking(
        self,
        service_id: str,
        employee_id: str | None,
        start_time: datetime,
        duration_minutes: int,
        booking_data: dict,
    ) -> Booking:
        """
        Check for overlapping bookings and create a new booking atomically.

        Uses pessimistic locking (SELECT ... FOR UPDATE) to prevent double-booking:
        1. Locks all bookings for the same service within the time window
        2. If any overlapping booking found, raises conflict
        3. If clear, creates the booking atomically

        Args:
            service_id: ID of the service being booked
            employee_id: ID of the employee (may be None)
            start_time: Start time of the booking
            duration_minutes: Duration of the service in minutes
            booking_data: Dictionary with booking details (id, customer_name, etc.)

        Returns:
            Created Booking entity

        Raises:
            HTTPException(409): If overlapping booking found
        """
        # Calculate the end time of this booking
        end_time = self._calculate_booking_end_time(start_time, duration_minutes)

        # Query for overlapping bookings with FOR UPDATE lock
        # An overlap occurs if:
        # - Booking is for the same service
        # - Booking's start_time is before our end_time AND
        # - Booking's end_time is after our start_time
        # We need to calculate each existing booking's end_time to check overlap

        stmt = (
            select(Booking)
            .where(Booking.service_id == service_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        existing_bookings = result.scalars().all()

        # Check for overlaps with the new booking time window
        for booking in existing_bookings:
            # For existing booking: check if it overlaps with [start_time, end_time)
            # Existing booking occupies: [booking.start_time, booking.start_time + duration)
            # To get duration, we need the service - but we already have duration_minutes
            # We'll assume all bookings use the same service (they do in this query)
            booking_end_time = self._calculate_booking_end_time(booking.start_time, duration_minutes)

            # Check overlap: existing_start < new_end AND new_start < existing_end
            if booking.start_time < end_time and start_time < booking_end_time:
                raise HTTPException(
                    status_code=409,
                    detail="Slot already booked"
                )

        # No conflicts found, create the booking
        booking = await self.create(booking_data)
        return booking


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

    def add(
        self,
        customer_name: str,
        service: str,
        slot: str,
        employee_id: str | None = None,
    ) -> dict[str, str | None]:
        """Create and add a booking (backward compatibility method)."""
        from uuid import uuid4
        booking = {
            "id": str(uuid4()),
            "customer_name": customer_name,
            "service": service,
            "slot": slot,
            "employee_id": employee_id,
            "status": "confirmed",
        }
        self.bookings[booking["id"]] = booking
        return booking

    def cancel(self, booking_id: str) -> dict[str, str | None]:
        """Cancel a booking (backward compatibility method)."""
        booking = self.get(booking_id)
        booking["status"] = "cancelled"
        return booking

    def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]:
        """Reschedule a booking (backward compatibility method)."""
        booking = self.get(booking_id)
        booking["slot"] = slot
        return booking


_repository = InMemoryBookingRepository()


def get_booking_repository() -> InMemoryBookingRepository:
    return _repository
