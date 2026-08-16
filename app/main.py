import logging

from fastapi import FastAPI

from app.routers import availability, bookings, businesses, employees, services

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(businesses.router)
app.include_router(bookings.router)
app.include_router(services.router)
app.include_router(employees.router)
app.include_router(availability.router)
