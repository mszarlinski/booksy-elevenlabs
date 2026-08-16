"""Repository for Booking entity."""

from typing import List
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
