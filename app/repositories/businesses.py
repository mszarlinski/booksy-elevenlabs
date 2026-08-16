"""Repository for Business entity."""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Business, Employee, Service
from app.repositories.base import BaseRepository


class BusinessRepository(BaseRepository[Business]):
    """Repository for Business entity with join queries."""

    def __init__(self, session: AsyncSession):
        """Initialize BusinessRepository."""
        super().__init__(session, Business)

    async def get_employees_by_business_id(self, business_id: str) -> List[Employee]:
        """
        Get all employees for a business.

        Args:
            business_id: ID of the business

        Returns:
            List of Employee entities
        """
        stmt = (
            select(Employee)
            .where(Employee.business_id == business_id)
            .order_by(Employee.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_services_by_business_id(self, business_id: str) -> List[Service]:
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
class InMemoryBusinessRepository:
    def __init__(self) -> None:
        self._businesses: list[dict[str, str]] = [
            {"id": "biz-glow-salon", "name": "Glow Hair & Beauty Salon"},
            {"id": "biz-downtown-barber", "name": "Downtown Barbershop"},
        ]

    def list(self) -> list[dict[str, str]]:
        return self._businesses

    def add(self, business: dict[str, str]) -> None:
        self._businesses.append(business)


_repository = InMemoryBusinessRepository()


def get_business_repository() -> InMemoryBusinessRepository:
    return _repository
