import logging

from fastapi import APIRouter, Depends

from app.repositories.employees import InMemoryEmployeeRepository, get_employee_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/employees")
def search_employees(
    service_id: str | None = None,
    repository: InMemoryEmployeeRepository = Depends(get_employee_repository),
) -> dict[str, list[dict[str, str | list[str]]]]:
    logger.info("tool_request tool=search_employees service_id=%s", service_id)
    employees = repository.search(service_id)
    logger.info("tool_response tool=search_employees result_count=%d", len(employees))
    return {"employees": employees}
