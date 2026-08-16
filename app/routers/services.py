import logging

from fastapi import APIRouter, Depends

from app.repositories.services import InMemoryServiceRepository, get_service_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/services")
def search_services(
    name: str | None = None,
    repository: InMemoryServiceRepository = Depends(get_service_repository),
) -> dict[str, list[dict[str, str | int | float]]]:
    logger.info("tool_request tool=search_services name=%s", name)
    services = repository.search(name)
    logger.info("tool_response tool=search_services result_count=%d", len(services))
    return {"services": services}
