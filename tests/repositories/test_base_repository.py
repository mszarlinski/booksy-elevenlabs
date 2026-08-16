"""Tests for BaseRepository CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Business
from app.repositories.base import BaseRepository


@pytest.mark.asyncio
async def test_get_by_id_success(async_session: AsyncSession):
    """Test retrieving entity by id."""
    repo = BaseRepository(async_session, Business)

    # Create test entity
    created = await repo.create({"id": "test-biz-1", "name": "Test Business"})

    # Retrieve it
    retrieved = await repo.get_by_id("test-biz-1")

    assert retrieved.id == "test-biz-1"
    assert retrieved.name == "Test Business"


@pytest.mark.asyncio
async def test_get_by_id_not_found(async_session: AsyncSession):
    """Test get_by_id raises ValueError when entity not found."""
    repo = BaseRepository(async_session, Business)

    with pytest.raises(ValueError, match="Business with id nonexistent not found"):
        await repo.get_by_id("nonexistent")


@pytest.mark.asyncio
async def test_list_empty(async_session: AsyncSession):
    """Test listing entities when none exist."""
    repo = BaseRepository(async_session, Business)

    entities = await repo.list()

    assert entities == []


@pytest.mark.asyncio
async def test_list_multiple(async_session: AsyncSession):
    """Test listing multiple entities."""
    repo = BaseRepository(async_session, Business)

    # Create multiple
    await repo.create({"id": "biz-1", "name": "Business 1"})
    await repo.create({"id": "biz-2", "name": "Business 2"})
    await repo.create({"id": "biz-3", "name": "Business 3"})

    entities = await repo.list()

    assert len(entities) == 3


@pytest.mark.asyncio
async def test_list_with_limit(async_session: AsyncSession):
    """Test listing with limit."""
    repo = BaseRepository(async_session, Business)

    for i in range(5):
        await repo.create({"id": f"biz-{i}", "name": f"Business {i}"})

    entities = await repo.list(limit=2)

    assert len(entities) == 2


@pytest.mark.asyncio
async def test_create_success(async_session: AsyncSession):
    """Test creating entity."""
    repo = BaseRepository(async_session, Business)

    created = await repo.create({
        "id": "new-biz",
        "name": "New Business",
        "description": "Test description"
    })

    assert created.id == "new-biz"
    assert created.name == "New Business"
    assert created.description == "Test description"


@pytest.mark.asyncio
async def test_update_success(async_session: AsyncSession):
    """Test updating entity."""
    repo = BaseRepository(async_session, Business)

    # Create
    await repo.create({"id": "biz-update", "name": "Original Name"})

    # Update
    updated = await repo.update("biz-update", {"name": "Updated Name"})

    assert updated.name == "Updated Name"

    # Verify persistence
    retrieved = await repo.get_by_id("biz-update")
    assert retrieved.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_not_found(async_session: AsyncSession):
    """Test update raises ValueError when entity not found."""
    repo = BaseRepository(async_session, Business)

    with pytest.raises(ValueError, match="Business with id nonexistent not found"):
        await repo.update("nonexistent", {"name": "New Name"})


@pytest.mark.asyncio
async def test_delete_success(async_session: AsyncSession):
    """Test deleting entity."""
    repo = BaseRepository(async_session, Business)

    # Create
    await repo.create({"id": "biz-delete", "name": "To Delete"})

    # Delete
    await repo.delete("biz-delete")

    # Verify deleted
    with pytest.raises(ValueError):
        await repo.get_by_id("biz-delete")


@pytest.mark.asyncio
async def test_delete_not_found(async_session: AsyncSession):
    """Test delete raises ValueError when entity not found."""
    repo = BaseRepository(async_session, Business)

    with pytest.raises(ValueError, match="Business with id nonexistent not found"):
        await repo.delete("nonexistent")


@pytest.mark.asyncio
async def test_exists_true(async_session: AsyncSession):
    """Test exists returns True for existing entity."""
    repo = BaseRepository(async_session, Business)

    await repo.create({"id": "biz-exists", "name": "Exists"})

    assert await repo.exists("biz-exists") is True


@pytest.mark.asyncio
async def test_exists_false(async_session: AsyncSession):
    """Test exists returns False for non-existing entity."""
    repo = BaseRepository(async_session, Business)

    assert await repo.exists("nonexistent") is False
