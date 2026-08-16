"""Tests for EmployeeRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Employee, Business, Booking, Service
from app.repositories.employees import EmployeeRepository
from datetime import datetime


@pytest.mark.asyncio
async def test_employee_repository_inherits_crud(async_session: AsyncSession):
    """Test EmployeeRepository has CRUD operations from base."""
    # Create parent business
    business = Business(id="biz-1", name="Test Business")
    async_session.add(business)
    await async_session.flush()

    repo = EmployeeRepository(async_session)

    created = await repo.create({
        "id": "emp-1",
        "business_id": "biz-1",
        "name": "John",
        "email": "john@test.com"
    })

    assert created.id == "emp-1"
    assert created.business_id == "biz-1"
    assert created.name == "John"


@pytest.mark.asyncio
async def test_get_bookings_by_employee_id(async_session: AsyncSession):
    """Test retrieving all bookings for an employee."""
    # Setup
    business = Business(id="biz-1", name="Test Business")
    employee = Employee(id="emp-1", business_id="biz-1", name="John")
    service = Service(
        id="svc-1",
        business_id="biz-1",
        name="Haircut",
        duration_minutes=30
    )

    async_session.add(business)
    async_session.add(employee)
    async_session.add(service)
    await async_session.flush()

    # Add bookings
    booking1 = Booking(
        id="book-1",
        customer_name="Alice",
        service_id="svc-1",
        employee_id="emp-1",
        start_time=datetime(2024, 8, 20, 10, 0),
        status="confirmed"
    )
    booking2 = Booking(
        id="book-2",
        customer_name="Bob",
        service_id="svc-1",
        employee_id="emp-1",
        start_time=datetime(2024, 8, 20, 11, 0),
        status="confirmed"
    )
    async_session.add(booking1)
    async_session.add(booking2)
    await async_session.flush()

    # Test
    repo = EmployeeRepository(async_session)
    bookings = await repo.get_bookings_by_employee_id("emp-1")

    assert len(bookings) == 2
    assert all(b.employee_id == "emp-1" for b in bookings)


@pytest.mark.asyncio
async def test_get_bookings_by_employee_id_empty(async_session: AsyncSession):
    """Test get_bookings_by_employee_id returns empty list when no bookings."""
    business = Business(id="biz-1", name="Test Business")
    employee = Employee(id="emp-1", business_id="biz-1", name="John")
    async_session.add(business)
    async_session.add(employee)
    await async_session.flush()

    repo = EmployeeRepository(async_session)
    bookings = await repo.get_bookings_by_employee_id("emp-1")

    assert bookings == []


@pytest.mark.asyncio
async def test_get_by_business_id(async_session: AsyncSession):
    """Test retrieving employees by business ID."""
    business = Business(id="biz-1", name="Test Business")
    emp1 = Employee(id="emp-1", business_id="biz-1", name="Alice")
    emp2 = Employee(id="emp-2", business_id="biz-1", name="Bob")
    emp3 = Employee(id="emp-3", business_id="biz-2", name="Carol")

    async_session.add(business)
    async_session.add(emp1)
    async_session.add(emp2)
    async_session.add(emp3)
    await async_session.flush()

    repo = EmployeeRepository(async_session)
    employees = await repo.get_by_business_id("biz-1")

    assert len(employees) == 2
    assert all(e.business_id == "biz-1" for e in employees)
