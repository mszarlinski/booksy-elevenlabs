from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.repositories.businesses import InMemoryBusinessRepository, get_business_repository

router = APIRouter()


class BusinessHttpBody(BaseModel):
    name: str


@router.get("/businesses")
def get_businesses(
    repository: InMemoryBusinessRepository = Depends(get_business_repository),
) -> dict[str, list[dict[str, str]]]:
    return {"businesses": repository.list()}


@router.post("/businesses")
def create_business(
    business: BusinessHttpBody,
    repository: InMemoryBusinessRepository = Depends(get_business_repository),
) -> dict[str, str]:
    created = {"id": str(uuid4()), "name": business.name}
    repository.add(created)
    return created
