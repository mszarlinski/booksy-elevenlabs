from collections.abc import Callable

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.idempotency import InMemoryIdempotencyStore, get_idempotency_store
from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository

router = APIRouter()


class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str


class RescheduleBookingRequest(BaseModel):
    slot: str


def _maybe_idempotent(
    idempotency_key: str | None,
    idempotency: InMemoryIdempotencyStore,
    mutate: Callable[[], dict[str, str]],
) -> dict[str, str]:
    if idempotency_key is None:
        return mutate()
    return idempotency.get_or_create(idempotency_key, mutate)


@router.get("/bookings")
def get_bookings(
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str]]]:
    return {"bookings": repository.list()}


@router.post("/bookings")
def create_booking(
    body: CreateBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str]:
    return _maybe_idempotent(
        idempotency_key,
        idempotency,
        lambda: repository.add(body.customer_name, body.service, body.slot),
    )


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str]:
    return _maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.cancel(booking_id)
    )


@router.post("/bookings/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: str,
    body: RescheduleBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str]:
    return _maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.reschedule(booking_id, body.slot)
    )
