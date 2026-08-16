"""Tests for ServiceRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Service, Business, Booking
from app.repositories.services import ServiceRepository
from datetime import datetime


@pytest.mark.asyncio
async def test_service_repository_inherits_crud(async_session: AsyncSession):
    """Test ServiceRepository has CRUD operations from base."""
    business = Business(id="biz-1", name="Test Business")
    async_session.add(business)
    await async_session.flush()

    repo = ServiceRepository(async_session)

    created = await repo.create({
        "id": "svc-1",
        "business_id": "biz-1",
        "name": "Haircut",
        "duration_minutes": 30
    })

    assert created.id == "svc-1"
    assert created.duration_minutes == 30


@pytest.mark.asyncio
async def test_get_bookings_by_service_id(async_session: AsyncSession):
    """Test retrieving all bookings for a service."""
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

    # Test
    repo = ServiceRepository(async_session)
    bookings = await repo.get_bookings_by_service_id("svc-1")

    assert len(bookings) == 2
    assert all(b.service_id == "svc-1" for b in bookings)


@pytest.mark.asyncio
async def test_get_bookings_by_service_id_empty(async_session: AsyncSession):
    """Test get_bookings_by_service_id returns empty list when no bookings."""
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

    repo = ServiceRepository(async_session)
    bookings = await repo.get_bookings_by_service_id("svc-1")

    assert bookings == []


@pytest.mark.asyncio
async def test_get_by_business_id(async_session: AsyncSession):
    """Test retrieving services by business ID."""
    business = Business(id="biz-1", name="Test Business")
    other_business = Business(id="biz-2", name="Other Business")
    svc1 = Service(id="svc-1", business_id="biz-1", name="Haircut", duration_minutes=30)
    svc2 = Service(id="svc-2", business_id="biz-1", name="Shave", duration_minutes=20)
    svc3 = Service(id="svc-3", business_id="biz-2", name="Manicure", duration_minutes=45)

    async_session.add(business)
    async_session.add(other_business)
    async_session.add(svc1)
    async_session.add(svc2)
    async_session.add(svc3)
    await async_session.flush()

    repo = ServiceRepository(async_session)
    services = await repo.get_by_business_id("biz-1")

    assert len(services) == 2
    assert all(s.business_id == "biz-1" for s in services)
