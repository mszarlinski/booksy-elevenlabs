"""Integration tests for multiple repositories working together."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models import Business, Employee, Service, Booking
from app.repositories import (
    BusinessRepository,
    EmployeeRepository,
    ServiceRepository,
    BookingRepository,
)


@pytest.mark.asyncio
async def test_complete_booking_workflow(async_session: AsyncSession):
    """Test complete workflow: create business, employees, services, bookings."""
    # Create repositories
    biz_repo = BusinessRepository(async_session)
    emp_repo = EmployeeRepository(async_session)
    svc_repo = ServiceRepository(async_session)
    book_repo = BookingRepository(async_session)

    # 1. Create a business
    business = await biz_repo.create({
        "id": "test-salon",
        "name": "Test Salon",
        "description": "A test beauty salon"
    })
    assert business.id == "test-salon"

    # 2. Add employees to business
    alice = await emp_repo.create({
        "id": "emp-alice",
        "business_id": "test-salon",
        "name": "Alice",
        "email": "alice@test.com"
    })
    bob = await emp_repo.create({
        "id": "emp-bob",
        "business_id": "test-salon",
        "name": "Bob",
        "email": "bob@test.com"
    })

    # 3. Get employees for business
    business_employees = await biz_repo.get_employees_by_business_id("test-salon")
    assert len(business_employees) == 2

    # 4. Add services to business
    haircut = await svc_repo.create({
        "id": "svc-haircut",
        "business_id": "test-salon",
        "name": "Men's Haircut",
        "duration_minutes": 30
    })
    shave = await svc_repo.create({
        "id": "svc-shave",
        "business_id": "test-salon",
        "name": "Shave",
        "duration_minutes": 20
    })

    # 5. Get services for business
    business_services = await biz_repo.get_services_by_business_id("test-salon")
    assert len(business_services) == 2

    # 6. Create bookings
    booking1 = await book_repo.create({
        "id": "book-1",
        "customer_name": "Customer A",
        "service_id": "svc-haircut",
        "employee_id": "emp-alice",
        "start_time": datetime(2024, 8, 20, 10, 0),
        "status": "confirmed"
    })
    booking2 = await book_repo.create({
        "id": "book-2",
        "customer_name": "Customer B",
        "service_id": "svc-shave",
        "employee_id": "emp-bob",
        "start_time": datetime(2024, 8, 20, 11, 0),
        "status": "pending"
    })

    # 7. Get bookings for service
    haircut_bookings = await svc_repo.get_bookings_by_service_id("svc-haircut")
    assert len(haircut_bookings) == 1
    assert haircut_bookings[0].customer_name == "Customer A"

    # 8. Get bookings for employee
    alice_bookings = await emp_repo.get_bookings_by_employee_id("emp-alice")
    assert len(alice_bookings) == 1
    assert alice_bookings[0].customer_name == "Customer A"

    # 9. Get bookings by status
    pending = await book_repo.get_by_status("pending")
    assert len(pending) == 1
    assert pending[0].customer_name == "Customer B"


@pytest.mark.asyncio
async def test_transaction_isolation(async_session: AsyncSession):
    """Test that repositories work with transaction isolation."""
    repo = BusinessRepository(async_session)

    # Create within transaction
    async with async_session.begin():
        business = await repo.create({
            "id": "tx-biz",
            "name": "Transaction Test"
        })

    # Verify created
    retrieved = await repo.get_by_id("tx-biz")
    assert retrieved.name == "Transaction Test"


@pytest.mark.asyncio
async def test_cascade_delete_behavior(async_session: AsyncSession):
    """Test that deleting business cascades to related entities."""
    biz_repo = BusinessRepository(async_session)
    emp_repo = EmployeeRepository(async_session)

    # Create business
    business = await biz_repo.create({
        "id": "cascade-biz",
        "name": "Cascade Test"
    })

    # Create employee
    employee = await emp_repo.create({
        "id": "cascade-emp",
        "business_id": "cascade-biz",
        "name": "Employee"
    })

    # Delete business
    await biz_repo.delete("cascade-biz")

    # Verify employee is gone (cascade delete)
    with pytest.raises(ValueError):
        await emp_repo.get_by_id("cascade-emp")
