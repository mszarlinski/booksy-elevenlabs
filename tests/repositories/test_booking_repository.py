"""Tests for BookingRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Booking, Business, Service, Employee
from app.repositories.bookings import BookingRepository
from datetime import datetime


@pytest.mark.asyncio
async def test_booking_repository_inherits_crud(async_session: AsyncSession):
    """Test BookingRepository has CRUD operations from base."""
    # Setup
    business = Business(id="biz-1", name="Test Business")
    service = Service(
        id="svc-1",
        business_id="biz-1",
        name="Haircut",
        duration_minutes=30
    )
    async_session.add(business)
    async_session.add(service)
    await async_session.flush()

    repo = BookingRepository(async_session)

    created = await repo.create({
        "id": "book-1",
        "customer_name": "John",
        "service_id": "svc-1",
        "start_time": datetime(2024, 8, 20, 10, 0),
        "status": "confirmed"
    })

    assert created.id == "book-1"
    assert created.customer_name == "John"


@pytest.mark.asyncio
async def test_get_by_service_id(async_session: AsyncSession):
    """Test retrieving bookings by service ID."""
    # Setup
    business = Business(id="biz-1", name="Test Business")
    service = Service(
        id="svc-1",
        business_id="biz-1",
        name="Haircut",
        duration_minutes=30
    )
    async_session.add(business)
    async_session.add(service)
    await async_session.flush()

    # Add bookings
    booking1 = Booking(
        id="book-1",
        customer_name="Alice",
        service_id="svc-1",
        start_time=datetime(2024, 8, 20, 10, 0),
        status="confirmed"
    )
    booking2 = Booking(
        id="book-2",
        customer_name="Bob",
        service_id="svc-1",
        start_time=datetime(2024, 8, 20, 11, 0),
        status="confirmed"
    )
    async_session.add(booking1)
    async_session.add(booking2)
    await async_session.flush()

    repo = BookingRepository(async_session)
    bookings = await repo.get_by_service_id("svc-1")

    assert len(bookings) == 2
    assert all(b.service_id == "svc-1" for b in bookings)


@pytest.mark.asyncio
async def test_get_by_employee_id(async_session: AsyncSession):
    """Test retrieving bookings by employee ID."""
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
        status="pending"
    )
    async_session.add(booking1)
    async_session.add(booking2)
    await async_session.flush()

    repo = BookingRepository(async_session)
    bookings = await repo.get_by_employee_id("emp-1")

    assert len(bookings) == 2
    assert all(b.employee_id == "emp-1" for b in bookings)


@pytest.mark.asyncio
async def test_get_by_status(async_session: AsyncSession):
    """Test retrieving bookings by status."""
    # Setup
    business = Business(id="biz-1", name="Test Business")
    service = Service(
        id="svc-1",
        business_id="biz-1",
        name="Haircut",
        duration_minutes=30
    )
    async_session.add(business)
    async_session.add(service)
    await async_session.flush()

    # Add bookings with different statuses
    booking1 = Booking(
        id="book-1",
        customer_name="Alice",
        service_id="svc-1",
        start_time=datetime(2024, 8, 20, 10, 0),
        status="confirmed"
    )
    booking2 = Booking(
        id="book-2",
        customer_name="Bob",
        service_id="svc-1",
        start_time=datetime(2024, 8, 20, 11, 0),
        status="pending"
    )
    booking3 = Booking(
        id="book-3",
        customer_name="Carol",
        service_id="svc-1",
        start_time=datetime(2024, 8, 20, 12, 0),
        status="confirmed"
    )
    async_session.add(booking1)
    async_session.add(booking2)
    async_session.add(booking3)
    await async_session.flush()

    repo = BookingRepository(async_session)
    confirmed = await repo.get_by_status("confirmed")

    assert len(confirmed) == 2
    assert all(b.status == "confirmed" for b in confirmed)
