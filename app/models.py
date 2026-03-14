from sqlalchemy import Column, Integer, String, Enum, DateTime
from datetime import datetime
from .database import Base

import enum

class BookingStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    seat_number = Column(String(50))
    status = Column(String(20), default=BookingStatus.PENDING_PAYMENT)
    created_at = Column(DateTime, default=datetime.utcnow)
