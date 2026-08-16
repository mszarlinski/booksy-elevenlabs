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


# In-memory repository used by the existing (non-DB-backed) routers.
class InMemoryServiceRepository:
    def __init__(self) -> None:
        self._services: list[dict[str, str | int | float]] = [
            {
                "id": "svc-haircut",
                "name": "Men's Haircut",
                "duration_minutes": 30,
                "price": 40.0,
            },
            {
                "id": "svc-shave",
                "name": "Shave",
                "duration_minutes": 20,
                "price": 25.0,
            },
            {
                "id": "svc-manicure",
                "name": "Manicure",
                "duration_minutes": 45,
                "price": 35.0,
            },
        ]

    def search(self, name: str | None = None) -> list[dict[str, str | int | float]]:
        if name is None:
            return self._services
        needle = name.lower()
        return [service for service in self._services if needle in service["name"].lower()]

    def get(self, service_id: str) -> dict[str, str | int | float]:
        for service in self._services:
            if service["id"] == service_id:
                return service
        raise KeyError(service_id)


_repository = InMemoryServiceRepository()


def get_service_repository() -> InMemoryServiceRepository:
    return _repository
