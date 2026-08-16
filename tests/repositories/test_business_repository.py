"""Tests for BusinessRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Business, Employee, Service
from app.repositories.businesses import BusinessRepository


@pytest.mark.asyncio
async def test_business_repository_inherits_crud(async_session: AsyncSession):
    """Test BusinessRepository has CRUD operations from base."""
    repo = BusinessRepository(async_session)

    created = await repo.create({
        "id": "biz-1",
        "name": "Test Business",
        "description": "Test description"
    })

    assert created.id == "biz-1"
    assert created.name == "Test Business"


@pytest.mark.asyncio
async def test_get_employees_by_business_id(async_session: AsyncSession):
    """Test retrieving all employees for a business."""
    biz_repo = BusinessRepository(async_session)

    # Create business
    business = await biz_repo.create({
        "id": "biz-emp-test",
        "name": "Business with Employees"
    })

    # Add employees directly
    emp1 = Employee(
        id="emp-1",
        business_id="biz-emp-test",
        name="Alice",
        email="alice@test.com"
    )
    emp2 = Employee(
        id="emp-2",
        business_id="biz-emp-test",
        name="Bob",
        email="bob@test.com"
    )
    async_session.add(emp1)
    async_session.add(emp2)
    await async_session.flush()

    # Get employees
    employees = await biz_repo.get_employees_by_business_id("biz-emp-test")

    assert len(employees) == 2
    assert any(e.name == "Alice" for e in employees)
    assert any(e.name == "Bob" for e in employees)


@pytest.mark.asyncio
async def test_get_services_by_business_id(async_session: AsyncSession):
    """Test retrieving all services for a business."""
    biz_repo = BusinessRepository(async_session)

    # Create business
    business = await biz_repo.create({
        "id": "biz-svc-test",
        "name": "Business with Services"
    })

    # Add services directly
    svc1 = Service(
        id="svc-1",
        business_id="biz-svc-test",
        name="Haircut",
        duration_minutes=30
    )
    svc2 = Service(
        id="svc-2",
        business_id="biz-svc-test",
        name="Shave",
        duration_minutes=20
    )
    async_session.add(svc1)
    async_session.add(svc2)
    await async_session.flush()

    # Get services
    services = await biz_repo.get_services_by_business_id("biz-svc-test")

    assert len(services) == 2
    assert any(s.name == "Haircut" for s in services)
    assert any(s.name == "Shave" for s in services)


@pytest.mark.asyncio
async def test_get_employees_by_business_id_empty(async_session: AsyncSession):
    """Test get_employees_by_business_id returns empty list when no employees."""
    biz_repo = BusinessRepository(async_session)

    await biz_repo.create({"id": "biz-no-emp", "name": "No Employees"})

    employees = await biz_repo.get_employees_by_business_id("biz-no-emp")

    assert employees == []
