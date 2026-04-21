from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, unique=True, nullable=False, primary_key=True)
    email = Column(String(255), nullable=False)
    password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    schedules = relationship("Schedule", back_populates="user")
    stock_history = relationship("StockHistory", back_populates="user")


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

    schedule = relationship("Schedule", back_populates="days")
    stock_history = relationship(
        "StockHistory",
        back_populates="schedule_day"
    )


class StockHistory(Base):
    __tablename__ = "stock_histoy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_day_id = Column(Integer, ForeignKey("schedule_days.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")  # pending | bought | refused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="stock_history")
    schedule_day = relationship("ScheduleDay", back_populates="stock_history")
