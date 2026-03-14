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
    # 1. Seat Availability Check (Event Service)
    try:
        event_response = requests.get(f"{EVENT_SERVICE_URL}/{booking_in.event_id}", timeout=2)
        if event_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Event not found or unavailable")
    except requests.exceptions.RequestException:
        print(f"WARNING: Event Service at {EVENT_SERVICE_URL} unreachable. Proceeding in TEST MODE.")

    # 2. Seat Locking (Database Check)
    # Check if this seat is already booked or pending payment
    existing_booking = db.query(models.Booking).filter(
        models.Booking.event_id == booking_in.event_id,
        models.Booking.seat_number == booking_in.seat_number,
        models.Booking.status.in_([models.BookingStatus.CONFIRMED, models.BookingStatus.PENDING_PAYMENT])
    ).first()

    if existing_booking:
        raise HTTPException(status_code=400, detail="Seat is already locked or booked")

    # 3. Create booking record with PENDING_PAYMENT status
    db_booking = models.Booking(
        user_id=booking_in.user_id,
        event_id=booking_in.event_id,
        seat_number=booking_in.seat_number,
        status=models.BookingStatus.PENDING_PAYMENT
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    # 4. Call Payment Service
    try:
        payment_payload = {
            "booking_id": db_booking.id,
            "user_id": db_booking.user_id,
            "amount": 100.0
        }
        payment_response = requests.post(PAYMENT_SERVICE_URL, json=payment_payload, timeout=2)
        
        if payment_response.status_code == 200:
            db_booking.status = models.BookingStatus.CONFIRMED
        else:
            db_booking.status = models.BookingStatus.EXPIRED  # Payment failed -> release seat
            
    except requests.exceptions.RequestException:
        # Bypassing for testing purposes
        print(f"WARNING: Payment Service at {PAYMENT_SERVICE_URL} unreachable. Confirming for demo.")
        db_booking.status = models.BookingStatus.CONFIRMED

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
    
    db_booking.status = models.BookingStatus.CANCELLED
    db.commit()
    return None
