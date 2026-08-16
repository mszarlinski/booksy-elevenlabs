"""Repository for Employee entity."""

from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Employee, Booking
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    """Repository for Employee entity with join queries."""

    def __init__(self, session: AsyncSession):
        """Initialize EmployeeRepository."""
        super().__init__(session, Employee)

    async def get_bookings_by_employee_id(self, employee_id: str) -> List[Booking]:
        """
        Get all bookings for an employee.

        Args:
            employee_id: ID of the employee

        Returns:
            List of Booking entities
        """
        stmt = (
            select(Booking)
            .where(Booking.employee_id == employee_id)
            .order_by(Booking.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_business_id(self, business_id: str) -> List[Employee]:
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


# In-memory repository used by the existing (non-DB-backed) routers.
class InMemoryEmployeeRepository:
    def __init__(self) -> None:
        self._employees: list[dict[str, str | list[str]]] = [
            {
                "id": "emp-alice",
                "name": "Alice",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-haircut", "svc-shave"],
            },
            {
                "id": "emp-carol",
                "name": "Carol",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-manicure"],
            },
            {
                "id": "emp-dave",
                "name": "Dave",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-manicure"],
            },
            {
                "id": "emp-bob",
                "name": "Bob",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-haircut", "svc-manicure"],
            },
            {
                "id": "emp-erin",
                "name": "Erin",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-shave"],
            },
            {
                "id": "emp-frank",
                "name": "Frank",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-shave"],
            },
        ]

    def search(self, service_id: str | None = None) -> list[dict[str, str | list[str]]]:
        if service_id is None:
            return self._employees
        return [
            employee for employee in self._employees if service_id in employee["service_ids"]
        ]

    def list(self) -> list[dict[str, str | list[str]]]:
        return self._employees

    def get(self, employee_id: str) -> dict[str, str | list[str]]:
        for employee in self._employees:
            if employee["id"] == employee_id:
                return employee
        raise KeyError(employee_id)


_repository = InMemoryEmployeeRepository()


def get_employee_repository() -> InMemoryEmployeeRepository:
    return _repository
