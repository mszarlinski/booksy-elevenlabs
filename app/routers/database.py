"""
Database example routes demonstrating dependency injection and database operations.

These routes serve as examples to verify that:
- The database dependency injection works correctly with FastAPI
- Sessions are properly created and cleaned up between requests
- Async database operations function as expected

NOTE: These are temporary example routes meant to demonstrate the pattern.
They should be removed before moving to production.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/db", tags=["Database"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    message: str
    timestamp: datetime


class TestRecordCreate(BaseModel):
    """Input model for creating test records - only accepts message from client."""

    message: str


class TestRecordResponse(BaseModel):
    """Output model for test records - includes database-generated fields."""

    id: int
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestDataResponse(BaseModel):
    """Response model for test data operations."""

    success: bool
    message: str
    records: list[TestRecordResponse] | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    """
    Simple database health check endpoint.

    This endpoint demonstrates:
    - Using the get_session dependency in a route handler
    - Executing a simple query to verify database connection
    - Session is automatically closed after the request completes

    Returns:
        HealthResponse with status and timestamp
    """
    try:
        # Simple query to test database connectivity
        result = await session.execute(text("SELECT 1 as status"))
        status = result.scalar()

        if status == 1:
            logger.info("Health check passed: database connection OK")
            return HealthResponse(
                status="healthy",
                message="Database connection successful",
                timestamp=datetime.now(),
            )
        else:
            logger.warning("Health check failed: unexpected database response")
            return HealthResponse(
                status="unhealthy",
                message="Unexpected database response",
                timestamp=datetime.now(),
            )

    except Exception as e:
        logger.error("Health check failed: %s", e)
        return HealthResponse(
            status="unhealthy",
            message=f"Database connection failed: {str(e)}",
            timestamp=datetime.now(),
        )


@router.post("/test", response_model=TestDataResponse)
async def create_test_record(
    body: TestRecordCreate, session: AsyncSession = Depends(get_session)
) -> TestDataResponse:
    """
    Create a test record by writing and immediately reading it back.

    This endpoint demonstrates:
    - Reading JSON request body
    - Executing a database INSERT statement
    - Executing a SELECT statement to retrieve the data
    - Using async transactions with session.begin()
    - Session cleanup after completion

    Args:
        body: TestRecordCreate with message field
        session: AsyncSession dependency provided by FastAPI

    Returns:
        TestDataResponse with success status and the created record
    """
    try:
        # Use explicit transaction for atomic operation
        async with session.begin():
            # Create a temporary table for test data
            await session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS test_records (
                    id SERIAL PRIMARY KEY,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                )
            )

            # Insert test record
            insert_query = text(
                """
                INSERT INTO test_records (message, created_at)
                VALUES (:message, CURRENT_TIMESTAMP)
                RETURNING id, message, created_at
                """
            )
            result = await session.execute(insert_query, {"message": body.message})
            record = result.fetchone()

            if record:
                logger.info("Test record created: id=%s, message=%s", record[0], record[1])
                return TestDataResponse(
                    success=True,
                    message="Test record created successfully",
                    records=[
                        TestRecordResponse(
                            id=record[0],
                            message=record[1],
                            created_at=record[2],
                        )
                    ],
                )
            else:
                logger.error("Failed to create test record: no result returned")
                return TestDataResponse(
                    success=False, message="Failed to create test record"
                )

    except Exception as e:
        logger.error("Error creating test record: %s", e)
        return TestDataResponse(
            success=False, message=f"Error creating test record: {str(e)}"
        )


@router.get("/test", response_model=TestDataResponse)
async def list_test_records(
    session: AsyncSession = Depends(get_session),
) -> TestDataResponse:
    """
    List all test records from the database.

    This endpoint demonstrates:
    - Querying multiple records from the database
    - Using the dependency injection pattern
    - Handling empty result sets
    - Session automatic cleanup

    Returns:
        TestDataResponse with list of all test records
    """
    try:
        # Query all test records
        select_query = text(
            """
            SELECT id, message, created_at
            FROM test_records
            ORDER BY created_at DESC
            """
        )
        result = await session.execute(select_query)
        records = result.fetchall()

        if records:
            logger.info("Retrieved %d test records", len(records))
            test_records = [
                TestRecordResponse(
                    id=record[0],
                    message=record[1],
                    created_at=record[2],
                )
                for record in records
            ]
            return TestDataResponse(
                success=True,
                message=f"Retrieved {len(records)} test records",
                records=test_records,
            )
        else:
            logger.info("No test records found in database")
            return TestDataResponse(
                success=True,
                message="No test records found",
                records=[],
            )

    except Exception as e:
        logger.error("Error querying test records: %s", e)
        return TestDataResponse(
            success=False, message=f"Error querying test records: {str(e)}"
        )
