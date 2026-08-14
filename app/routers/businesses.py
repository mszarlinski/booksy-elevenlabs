from fastapi import APIRouter

router = APIRouter()

businesses = []


@router.get("/businesses")
def get() -> dict[str, list]:
    return {"businesses": businesses}

@router.post("/businesses")
def post(business: Business):
    businesses.add(business)
