"""Repository for Employee entity."""

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
