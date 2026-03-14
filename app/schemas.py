from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BookingBase(BaseModel):
    user_id: int
    event_id: int
    seat_number: str

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
