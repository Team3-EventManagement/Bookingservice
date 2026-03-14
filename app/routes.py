from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import requests
import os

from . import models, schemas, database

router = APIRouter()

EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service/events")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service/payments")

@router.post("/bookings", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def create_booking(booking_in: schemas.BookingCreate, db: Session = Depends(database.get_db)):
    # 1. Check event availability via Event Service API
    try:
        event_response = requests.get(f"{EVENT_SERVICE_URL}/{booking_in.event_id}", timeout=5)
        if event_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Event not found or unavailable")
    except requests.exceptions.RequestException:
        # For demo purposes, we might want to continue or fail. 
        # Here we assume strict check.
        raise HTTPException(status_code=503, detail="Event service unavailable")

    # 2. Create booking record with PENDING status
    db_booking = models.Booking(
        user_id=booking_in.user_id,
        event_id=booking_in.event_id,
        seat_number=booking_in.seat_number,
        status="pending"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    # 3. Call Payment Service
    try:
        payment_payload = {
            "booking_id": db_booking.id,
            "user_id": db_booking.user_id,
            "amount": 100.0  # Placeholder amount
        }
        payment_response = requests.post(PAYMENT_SERVICE_URL, json=payment_payload, timeout=5)
        
        if payment_response.status_code == 200:
            db_booking.status = "confirmed"
        else:
            db_booking.status = "payment_failed"
            
    except requests.exceptions.RequestException:
        # In a real system, we'd use a message queue or background task to retry
        db_booking.status = "payment_pending"

    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.get("/bookings/{user_id}", response_model=List[schemas.Booking])
def get_user_bookings(user_id: int, db: Session = Depends(database.get_db)):
    bookings = db.query(models.Booking).filter(models.Booking.user_id == user_id).all()
    return bookings

@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(booking_id: int, db: Session = Depends(database.get_db)):
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db_booking.status = "cancelled"
    db.commit()
    return None
