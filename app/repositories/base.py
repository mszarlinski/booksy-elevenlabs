"""
Base repository class with common CRUD operations.

Provides standard patterns for all entity repositories:
- get_by_id(id): Get single entity by primary key
- list(): Get all entities
- create(data): Create new entity
- update(id, data): Update existing entity
- delete(id): Delete entity
"""

from typing import TypeVar, Generic, Type, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Type variable for entity model
T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Generic repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        Initialize repository with async session and model class.

        Args:
            session: AsyncSession instance for database operations
            model: SQLAlchemy ORM model class (e.g., Business, Employee)
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: str) -> T:
        """
        Get entity by primary key.

        Args:
            id: Primary key value

        Returns:
            Entity instance

        Raises:
            ValueError: If entity not found
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"{self.model.__name__} with id {id} not found")

        return entity

    async def list(self, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[T]:
        """
        List all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return (None = no limit)
            offset: Number of entities to skip (default: 0)

        Returns:
            List of entities
        """
        stmt = select(self.model)

        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: dict[str, Any]) -> T:
        """
        Create new entity.

        Args:
            data: Dictionary with entity fields

        Returns:
            Created entity instance
        """
        entity = self.model(**data)
        self.session.add(entity)
        await self.session.flush()  # Flush to get any DB-generated values
        return entity

    async def update(self, id: str, data: dict[str, Any]) -> T:
        """
        Update existing entity.

        Args:
            id: Primary key of entity to update
            data: Dictionary with fields to update

        Returns:
            Updated entity instance

        Raises:
            ValueError: If entity not found
        """
        entity = await self.get_by_id(id)

        # Update attributes
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, id: str) -> None:
        """
        Delete entity by primary key.

        Args:
            id: Primary key of entity to delete

        Raises:
            ValueError: If entity not found
        """
        entity = await self.get_by_id(id)
        await self.session.delete(entity)
        await self.session.flush()

    async def exists(self, id: str) -> bool:
        """
        Check if entity exists.

        Args:
            id: Primary key to check

        Returns:
            True if entity exists, False otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
