"""
SQLAlchemy ORM models for domain entities.

This module contains declarative ORM models that map to database tables:
- Business: Represents a business/organization
- Employee: Represents an employee working for a business
- Service: Represents a service offered by a business
- Booking: Represents a customer booking of a service with an employee
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Business(Base):
    """
    Business entity representing an organization/business.

    Relationships:
    - employees: One-to-many relationship with Employee
    - services: One-to-many relationship with Service
    """

    __tablename__ = "businesses"

    id = String(36, primary_key=True)
    name = String(255, nullable=False)
    description = Text(nullable=True)

    # Relationships
    employees = relationship(
        "Employee",
        back_populates="business",
        cascade="all, delete-orphan",
        doc="Employees working for this business",
    )
    services = relationship(
        "Service",
        back_populates="business",
        cascade="all, delete-orphan",
        doc="Services offered by this business",
    )


class Employee(Base):
    """
    Employee entity representing staff at a business.

    Relationships:
    - business: Many-to-one relationship with Business
    - bookings: One-to-many relationship with Booking
    """

    __tablename__ = "employees"

    id = String(36, primary_key=True)
    business_id = String(36, ForeignKey("businesses.id"), nullable=False)
    name = String(255, nullable=False)
    email = String(255, nullable=True)
    phone = String(20, nullable=True)

    # Relationships
    business = relationship(
        "Business",
        back_populates="employees",
        doc="Business this employee works for",
    )
    bookings = relationship(
        "Booking",
        back_populates="employee",
        cascade="all, delete-orphan",
        doc="Bookings assigned to this employee",
    )


class Service(Base):
    """
    Service entity representing a service offered by a business.

    Relationships:
    - business: Many-to-one relationship with Business
    - bookings: One-to-many relationship with Booking
    """

    __tablename__ = "services"

    id = String(36, primary_key=True)
    business_id = String(36, ForeignKey("businesses.id"), nullable=False)
    name = String(255, nullable=False)
    duration_minutes = Integer(nullable=False)

    # Relationships
    business = relationship(
        "Business",
        back_populates="services",
        doc="Business offering this service",
    )
    bookings = relationship(
        "Booking",
        back_populates="service",
        cascade="all, delete-orphan",
        doc="Bookings for this service",
    )


class Booking(Base):
    """
    Booking entity representing a customer's booking of a service with an employee.

    Relationships:
    - service: Many-to-one relationship with Service
    - employee: Many-to-one relationship with Employee (optional)
    """

    __tablename__ = "bookings"

    id = String(36, primary_key=True)
    customer_name = String(255, nullable=False)
    customer_email = String(255, nullable=True)
    service_id = String(36, ForeignKey("services.id"), nullable=False)
    employee_id = String(36, ForeignKey("employees.id"), nullable=True)
    start_time = DateTime(nullable=False)
    status = String(50, nullable=False, default="pending")

    # Relationships
    service = relationship(
        "Service",
        back_populates="bookings",
        doc="Service being booked",
    )
    employee = relationship(
        "Employee",
        back_populates="bookings",
        doc="Employee assigned to this booking (optional)",
    )
