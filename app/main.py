from fastapi import FastAPI

from app.routers import businesses

app = FastAPI()
app.include_router(businesses.router)
