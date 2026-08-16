"""Repository for Service entity."""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Service, Booking
from app.repositories.base import BaseRepository


class ServiceRepository(BaseRepository[Service]):
    """Repository for Service entity with join queries."""

    def __init__(self, session: AsyncSession):
        """Initialize ServiceRepository."""
        super().__init__(session, Service)

    async def get_bookings_by_service_id(self, service_id: str) -> List[Booking]:
        """
        Get all bookings for a service.

        Args:
            service_id: ID of the service

        Returns:
            List of Booking entities
        """
        stmt = (
            select(Booking)
            .where(Booking.service_id == service_id)
            .order_by(Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_business_id(self, business_id: str) -> List[Service]:
        """
        Get all services for a business.

        Args:
            business_id: ID of the business

        Returns:
            List of Service entities
        """
        stmt = (
            select(Service)
            .where(Service.business_id == business_id)
            .order_by(Service.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
