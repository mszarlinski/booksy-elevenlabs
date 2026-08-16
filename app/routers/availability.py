import logging

from fastapi import APIRouter, Depends, HTTPException

from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository
from app.repositories.employees import InMemoryEmployeeRepository, get_employee_repository
from app.repositories.services import InMemoryServiceRepository, get_service_repository
from app.slots import generate_available_slots

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/availability")
def search_available_slots(
    service_id: str,
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
    service_repository: InMemoryServiceRepository = Depends(get_service_repository),
    employee_repository: InMemoryEmployeeRepository = Depends(get_employee_repository),
    booking_repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str]]]:
    logger.info(
        "tool_request tool=search_available_slots service_id=%s date=%s "
        "earliest_time=%s latest_time=%s employee_id=%s",
        service_id,
        date,
        earliest_time,
        latest_time,
        employee_id,
    )
    try:
        service = service_repository.get(service_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown service_id: {service_id}")

    try:
        slots = generate_available_slots(
            service=service,
            employees=employee_repository.list(),
            bookings=booking_repository.list(),
            date=date,
            earliest_time=earliest_time,
            latest_time=latest_time,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("tool_response tool=search_available_slots result_count=%d", len(slots))
    return {"slots": slots}
