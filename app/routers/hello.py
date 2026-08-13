from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
def get_hello() -> dict[str, str]:
    return {"message": "Hello world!"}
