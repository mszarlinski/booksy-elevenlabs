import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.idempotency import InMemoryIdempotencyStore, get_idempotency_store, maybe_idempotent
from app.models import Booking
from app.repositories.bookings import BookingRepository, InMemoryBookingRepository, get_booking_repository
from app.repositories.services import ServiceRepository
from app.repositories.employees import EmployeeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
    confirmed: bool
    employee_id: str | None = None


class RescheduleBookingRequest(BaseModel):
    slot: str


@router.get("/bookings")
def get_bookings(
    customer_name: str | None = None,
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str | None]]]:
    bookings = repository.list()
    if customer_name is not None:
        logger.info("tool_request tool=get_customer_bookings customer_name_filter=true")
        needle = customer_name.lower()
        bookings = [b for b in bookings if needle in b["customer_name"].lower()]
        logger.info("tool_response tool=get_customer_bookings result_count=%d", len(bookings))
    return {"bookings": bookings}


@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str,
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, str | None]:
    logger.info("tool_request tool=get_booking booking_id=%s", booking_id)
    try:
        booking = repository.get(booking_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown booking_id: {booking_id}")
    logger.info(
        "tool_response tool=get_booking booking_id=%s status=%s", booking_id, booking["status"]
    )
    return booking


@router.post("/bookings")
def create_booking(
    body: CreateBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    logger.info(
        "tool_request tool=create_booking service=%s slot=%s employee_id=%s confirmed=%s",
        body.service,
        body.slot,
        body.employee_id,
        body.confirmed,
    )
    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="booking must be explicitly confirmed by the customer before creation",
        )
    booking = maybe_idempotent(
        idempotency_key,
        idempotency,
        lambda: repository.add(body.customer_name, body.service, body.slot, body.employee_id),
    )
    logger.info("tool_response tool=create_booking booking_id=%s", booking["id"])
    return booking


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    return maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.cancel(booking_id)
    )


@router.post("/bookings/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: str,
    body: RescheduleBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    return maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.reschedule(booking_id, body.slot)
    )


class CreateBookingWithValidationRequest(BaseModel):
    """Request model for creating a booking with full validation."""
    customer_name: str = Field(..., min_length=1, description="Customer name")
    customer_email: str = Field(..., description="Customer email address")
    service_id: str = Field(..., description="Service ID")
    employee_id: str = Field(..., description="Employee ID")
    start_time: str = Field(..., description="Start time in ISO 8601 format")


class BookingResponse(BaseModel):
    """Response model for booking details."""
    id: str
    customer_name: str
    customer_email: str | None
    service_id: str
    employee_id: str | None
    start_time: str
    status: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/bookings/validated",
    status_code=status.HTTP_201_CREATED,
    response_model=BookingResponse,
)
async def create_booking_with_validation(
    body: CreateBookingWithValidationRequest,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """
    Create a booking with full validation.

    Validates:
    - customer_name and customer_email are provided
    - service_id exists in database
    - employee_id exists in database (optional)
    - start_time is in valid ISO 8601 format
    - start_time is in the future

    Returns:
    - 201 Created with booking details if successful
    - 400 Bad Request for validation errors
    - 404 Not Found if service or employee not found
    """
    logger.info(
        "Creating booking: customer=%s, service_id=%s, employee_id=%s, start_time=%s",
        body.customer_name,
        body.service_id,
        body.employee_id,
        body.start_time,
    )

    if not body.customer_name or not body.customer_name.strip():
        logger.warning("Booking creation failed: customer_name is empty")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_name is required and cannot be empty",
        )

    if not body.customer_email or not body.customer_email.strip():
        logger.warning("Booking creation failed: customer_email is empty")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_email is required and cannot be empty",
        )

    try:
        start_time_dt = datetime.fromisoformat(body.start_time.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning("Booking creation failed: invalid start_time format=%s", body.start_time)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_time must be in ISO 8601 format, got: {body.start_time}",
        )

    # Normalize to naive UTC: bookings.start_time is TIMESTAMP WITHOUT TIME
    # ZONE, and comparing it against an aware datetime (in the overlap check
    # below) raises TypeError.
    if start_time_dt.tzinfo is not None:
        start_time_dt = start_time_dt.astimezone(timezone.utc).replace(tzinfo=None)

    if start_time_dt <= datetime.now(timezone.utc).replace(tzinfo=None):
        logger.warning("Booking creation failed: start_time is in the past")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be in the future",
        )

    # All reads and writes share one transaction: AsyncSession autobegins on
    # the first execute(), so starting session.begin() only after the service
    # and employee lookups would raise "a transaction is already begun".
    try:
        async with session.begin():
            service_repo = ServiceRepository(session)
            try:
                service = await service_repo.get_by_id(body.service_id)
                logger.info("Service found: id=%s, name=%s", service.id, service.name)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Service with id {body.service_id} not found",
                ) from e

            employee_repo = EmployeeRepository(session)
            try:
                employee = await employee_repo.get_by_id(body.employee_id)
                logger.info("Employee found: id=%s, name=%s", employee.id, employee.name)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with id {body.employee_id} not found",
                ) from e

            booking_repo = BookingRepository(session)
            booking_data = {
                "id": str(uuid4()),
                "customer_name": body.customer_name,
                "customer_email": body.customer_email,
                "service_id": body.service_id,
                "employee_id": body.employee_id,
                "start_time": start_time_dt,
                "status": "confirmed",
            }

            booking = await booking_repo.check_and_create_booking(
                employee_id=body.employee_id,
                start_time=start_time_dt,
                duration_minutes=service.duration_minutes,
                booking_data=booking_data,
            )
            logger.info("Booking created: id=%s, status=%s", booking.id, booking.status)

            return BookingResponse(
                id=booking.id,
                customer_name=booking.customer_name,
                customer_email=booking.customer_email,
                service_id=booking.service_id,
                employee_id=booking.employee_id,
                start_time=booking.start_time.isoformat(),
                status=booking.status,
            )
    except HTTPException as e:
        logger.warning("Booking creation failed: %s", e.detail)
        raise
    except Exception as e:
        logger.error("Error creating booking: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating booking",
        ) from e
