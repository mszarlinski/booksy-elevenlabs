import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine, async_session_factory, Base
from app.models import Business, Employee, Service, Booking  # Import models to register them
from app.routers import availability, bookings, businesses, employees, services, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.

    Startup: Initialize the database engine and create required tables
    Shutdown: Dispose of the database engine
    """
    # Startup: Initialize database engine and create tables
    logger.info("Starting up: Initializing database engine")
    try:
        # The engine is already created in app.database, but we can add
        # any additional initialization logic here if needed
        logger.info("Database engine initialized")

        # Create all ORM model tables on startup using metadata
        logger.info("Creating ORM model tables")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("ORM model tables created/verified successfully")

        # Create test_records table on startup (one-time initialization)
        async with async_session_factory() as session:
            try:
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
                await session.commit()
                logger.info("Test records table created/verified successfully")
            except Exception as e:
                logger.error("Failed to create test_records table: %s", e)
                raise

    except Exception as e:
        logger.error("Failed to initialize database engine: %s", e)
        raise

    yield  # Application is now running

    # Shutdown: Dispose of the engine
    logger.info("Shutting down: Disposing database engine")
    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error("Error disposing database engine: %s", e)


app = FastAPI(lifespan=lifespan)
app.include_router(businesses.router)
app.include_router(bookings.router)
app.include_router(services.router)
app.include_router(employees.router)
app.include_router(availability.router)
app.include_router(database.router, tags=["Database"])
