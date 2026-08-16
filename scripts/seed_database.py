"""
Seed script to populate the database with sample data.

This script is idempotent - it safely checks for existing data before inserting.
It can be run multiple times without creating duplicates.

Usage:
    python scripts/seed_database.py

Environment variables:
    DATABASE_URL: PostgreSQL connection string (default: constructed from POSTGRES_* vars)
    SQL_ECHO: Set to 'false' to disable SQL query logging (default: 'true')
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add the project root to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, async_session_factory, engine
from app.models import Business, Employee, Service, Booking


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Sample data definitions
BUSINESSES = [
    {
        "name": "Sweet Salon",
        "description": "Professional hair salon specializing in cuts, colors, and treatments",
    },
    {
        "name": "Elite Gym",
        "description": "Modern fitness center with personal training and group classes",
    },
]

EMPLOYEES_BY_BUSINESS = {
    "Sweet Salon": [
        {"name": "Alice Johnson", "email": "alice@sweetsalon.com", "phone": "555-0101"},
        {"name": "Bob Smith", "email": "bob@sweetsalon.com", "phone": "555-0102"},
        {"name": "Carol White", "email": "carol@sweetsalon.com", "phone": "555-0103"},
    ],
    "Elite Gym": [
        {"name": "David Brown", "email": "david@elitegym.com", "phone": "555-0201"},
        {"name": "Emma Davis", "email": "emma@elitegym.com", "phone": "555-0202"},
        {"name": "Frank Miller", "email": "frank@elitegym.com", "phone": "555-0203"},
        {"name": "Grace Lee", "email": "grace@elitegym.com", "phone": "555-0204"},
    ],
}

SERVICES_BY_BUSINESS = {
    "Sweet Salon": [
        {"name": "Haircut", "duration_minutes": 30},
        {"name": "Hair Color", "duration_minutes": 60},
        {"name": "Hair Treatment", "duration_minutes": 45},
    ],
    "Elite Gym": [
        {"name": "Personal Training Session", "duration_minutes": 60},
        {"name": "Group Fitness Class", "duration_minutes": 45},
        {"name": "Yoga Session", "duration_minutes": 60},
    ],
}

# Sample bookings to create (will be paired with existing entities)
SAMPLE_BOOKINGS = [
    {
        "customer_name": "John Anderson",
        "customer_email": "john.anderson@email.com",
        "days_offset": 1,
        "hours_offset": 10,
        "status": "pending",
    },
    {
        "customer_name": "Sarah Thompson",
        "customer_email": "sarah.thompson@email.com",
        "days_offset": 1,
        "hours_offset": 14,
        "status": "pending",
    },
    {
        "customer_name": "Michael Chen",
        "customer_email": "michael.chen@email.com",
        "days_offset": 2,
        "hours_offset": 11,
        "status": "pending",
    },
    {
        "customer_name": "Lisa Rodriguez",
        "customer_email": "lisa.rodriguez@email.com",
        "days_offset": 2,
        "hours_offset": 15,
        "status": "pending",
    },
]


async def create_tables() -> None:
    """Create all tables if they don't exist."""
    logger.info("Creating tables if needed...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Tables created or verified")
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        raise


async def check_existing_data(session: AsyncSession) -> bool:
    """
    Check if sample data already exists in the database.

    Returns:
        True if data exists, False otherwise
    """
    try:
        result = await session.execute(select(Business))
        businesses = result.scalars().all()
        return len(businesses) > 0
    except Exception as e:
        logger.error(f"Error checking existing data: {e}")
        raise


async def seed_businesses(session: AsyncSession) -> dict[str, str]:
    """
    Seed businesses into the database.

    Returns:
        Mapping of business name to business ID
    """
    logger.info("Seeding businesses...")
    business_ids: dict[str, str] = {}

    for business_data in BUSINESSES:
        business_id = str(uuid4())
        business = Business(
            id=business_id,
            name=business_data["name"],
            description=business_data["description"],
        )
        session.add(business)
        business_ids[business_data["name"]] = business_id
        logger.info(f"  • Added business: {business_data['name']} (ID: {business_id})")

    await session.commit()
    logger.info(f"✓ Seeded {len(BUSINESSES)} business(es)")
    return business_ids


async def seed_employees(
    session: AsyncSession, business_ids: dict[str, str]
) -> dict[str, list[str]]:
    """
    Seed employees into the database.

    Args:
        session: AsyncSession instance
        business_ids: Mapping of business name to business ID

    Returns:
        Mapping of business name to list of employee IDs
    """
    logger.info("Seeding employees...")
    employee_ids_by_business: dict[str, list[str]] = {}

    for business_name, business_id in business_ids.items():
        employee_ids: list[str] = []
        employees_data = EMPLOYEES_BY_BUSINESS.get(business_name, [])

        for employee_data in employees_data:
            employee_id = str(uuid4())
            employee = Employee(
                id=employee_id,
                business_id=business_id,
                name=employee_data["name"],
                email=employee_data.get("email"),
                phone=employee_data.get("phone"),
            )
            session.add(employee)
            employee_ids.append(employee_id)
            logger.info(
                f"  • Added employee: {employee_data['name']} "
                f"({business_name}) - ID: {employee_id}"
            )

        employee_ids_by_business[business_name] = employee_ids

    await session.commit()
    total_employees = sum(len(ids) for ids in employee_ids_by_business.values())
    logger.info(f"✓ Seeded {total_employees} employee(s)")
    return employee_ids_by_business


async def seed_services(
    session: AsyncSession, business_ids: dict[str, str]
) -> dict[str, list[str]]:
    """
    Seed services into the database.

    Args:
        session: AsyncSession instance
        business_ids: Mapping of business name to business ID

    Returns:
        Mapping of business name to list of service IDs
    """
    logger.info("Seeding services...")
    service_ids_by_business: dict[str, list[str]] = {}

    for business_name, business_id in business_ids.items():
        service_ids: list[str] = []
        services_data = SERVICES_BY_BUSINESS.get(business_name, [])

        for service_data in services_data:
            service_id = str(uuid4())
            service = Service(
                id=service_id,
                business_id=business_id,
                name=service_data["name"],
                duration_minutes=service_data["duration_minutes"],
            )
            session.add(service)
            service_ids.append(service_id)
            logger.info(
                f"  • Added service: {service_data['name']} "
                f"({business_name}) - Duration: {service_data['duration_minutes']}m - ID: {service_id}"
            )

        service_ids_by_business[business_name] = service_ids

    await session.commit()
    total_services = sum(len(ids) for ids in service_ids_by_business.values())
    logger.info(f"✓ Seeded {total_services} service(s)")
    return service_ids_by_business


async def seed_bookings(
    session: AsyncSession,
    business_ids: dict[str, str],
    employee_ids_by_business: dict[str, list[str]],
    service_ids_by_business: dict[str, list[str]],
) -> None:
    """
    Seed bookings into the database.

    Args:
        session: AsyncSession instance
        business_ids: Mapping of business name to business ID
        employee_ids_by_business: Mapping of business name to employee IDs
        service_ids_by_business: Mapping of business name to service IDs
    """
    logger.info("Seeding bookings...")
    bookings_created = 0

    # Get a list of businesses to cycle through
    business_names = list(business_ids.keys())
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for idx, booking_data in enumerate(SAMPLE_BOOKINGS):
        # Cycle through businesses and services
        business_name = business_names[idx % len(business_names)]
        services = service_ids_by_business[business_name]
        service_id = services[idx % len(services)]
        employees = employee_ids_by_business[business_name]
        employee_id = employees[idx % len(employees)]

        # Calculate start time
        start_time = base_time + timedelta(
            days=booking_data["days_offset"], hours=booking_data["hours_offset"]
        )

        booking_id = str(uuid4())
        booking = Booking(
            id=booking_id,
            customer_name=booking_data["customer_name"],
            customer_email=booking_data.get("customer_email"),
            service_id=service_id,
            employee_id=employee_id,
            start_time=start_time,
            status=booking_data["status"],
        )
        session.add(booking)
        bookings_created += 1
        logger.info(
            f"  • Added booking: {booking_data['customer_name']} "
            f"@ {start_time.strftime('%Y-%m-%d %H:%M')} "
            f"({business_name}) - ID: {booking_id}"
        )

    await session.commit()
    logger.info(f"✓ Seeded {bookings_created} booking(s)")


async def seed_database() -> None:
    """Main seeding function."""
    logger.info("Starting database seeding...")
    logger.info("-" * 60)

    try:
        # Create tables first
        await create_tables()

        # Create a session
        async with async_session_factory() as session:
            # Check if data already exists (idempotent)
            if await check_existing_data(session):
                logger.warning("✓ Sample data already exists, skipping seeding")
                logger.info("-" * 60)
                logger.info("Database already contains sample data.")
                return

            # Seed the data
            business_ids = await seed_businesses(session)
            employee_ids_by_business = await seed_employees(session, business_ids)
            service_ids_by_business = await seed_services(session, business_ids)
            await seed_bookings(
                session, business_ids, employee_ids_by_business, service_ids_by_business
            )

        logger.info("-" * 60)
        logger.info("✓ Database seeding completed successfully!")

    except Exception as e:
        logger.error(f"✗ Database seeding failed: {e}")
        logger.debug("", exc_info=True)
        raise


async def main() -> None:
    """Entry point for the seed script."""
    try:
        await seed_database()
    except KeyboardInterrupt:
        logger.info("\nSeeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        sys.exit(1)
    finally:
        # Close the engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
