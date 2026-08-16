import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.routers import availability, bookings, businesses, employees, services, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.

    Startup: Initialize the database engine
    Shutdown: Dispose of the database engine
    """
    # Startup: Initialize database engine
    logger.info("Starting up: Initializing database engine")
    try:
        # The engine is already created in app.database, but we can add
        # any additional initialization logic here if needed
        logger.info("Database engine initialized")
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
