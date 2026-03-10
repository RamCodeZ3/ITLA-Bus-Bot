from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, String, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    schedules = relationship("Schedule", back_populates="user")
    purchases = relationship("Purchase", back_populates="user")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    term = Column(String(20), nullable=False)  # e.g. "2026-1"
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="schedules")
    days = relationship("ScheduleDay", back_populates="schedule")


class ScheduleDay(Base):
    __tablename__ = "schedule_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    day = Column(String(10), nullable=False)  # monday | tuesday | ... | friday
    ticket_type = Column(String(20), nullable=False)  # round_trip | arrival | departure
    arrival_route = Column(Text)
    pickup_stop = Column(Text)
    departure_route = Column(Text)
    dropoff_stop = Column(Text)

    schedule = relationship("Schedule", back_populates="days")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    ticket_type = Column(String(20))  # round_trip | arrival | departure
    arrival_route = Column(Text)
    pickup_stop = Column(Text)
    departure_route = Column(Text)
    dropoff_stop = Column(Text)
    status = Column(String(20), default="pending")  # pending | success | failed
    pdf_path = Column(Text)
    purchased_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="purchases")
