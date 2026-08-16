import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.models import Business, Employee, Service, Booking  # noqa: F401 (register ORM models)
from app.routers import availability, bookings, businesses, employees, services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.

    Schema is owned exclusively by Alembic migrations (see MIGRATIONS.md) -
    this lifespan only disposes the engine on shutdown.
    """
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
