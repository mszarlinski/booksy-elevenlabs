from fastapi import FastAPI

from app.routers import bookings, businesses

app = FastAPI()
app.include_router(businesses.router)
app.include_router(bookings.router)
