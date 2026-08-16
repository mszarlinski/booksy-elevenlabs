import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.idempotency import InMemoryIdempotencyStore, get_idempotency_store, maybe_idempotent
from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
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
    return maybe_idempotent(
        idempotency_key,
        idempotency,
        lambda: repository.add(body.customer_name, body.service, body.slot, body.employee_id),
    )


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
