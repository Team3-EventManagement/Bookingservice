from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import requests
import os

from . import models, schemas, database, auth, rabbitmq

router = APIRouter()

EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8001/events")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002/payments")

@router.post("/bookings", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: schemas.BookingCreate, 
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(auth.get_current_user)
):
    # Security: Ensure user is only booking for themselves
    if booking_in.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only book for yourself")

    # 1. Seat Availability & Price Check (Event Service)
    event_data = None
    try:
        event_response = requests.get(f"{EVENT_SERVICE_URL}/{booking_in.event_id}", timeout=2)
        if event_response.status_code == 200:
            event_data = event_response.json()
        else:
            raise HTTPException(status_code=404, detail="Event not found or unavailable")
    except requests.exceptions.RequestException:
        print(f"WARNING: Event Service at {EVENT_SERVICE_URL} unreachable. Proceeding in TEST MODE.")
        # Mock data for testing if service is offline
        event_data = {"price": 100.0, "name": "Test Event"}

    # 2. Seat Locking (Database Check)
    occupied = db.query(models.Booking).filter(
        models.Booking.event_id == booking_in.event_id,
        models.Booking.seat_number == booking_in.seat_number,
        models.Booking.status.in_([models.BookingStatus.CONFIRMED, models.BookingStatus.PENDING_PAYMENT])
    ).first()

    if occupied:
        raise HTTPException(status_code=400, detail="Seat already locked or booked")

    # 3. Create booking record with PENDING_PAYMENT status
    db_booking = models.Booking(
        user_id=current_user_id,
        event_id=booking_in.event_id,
        seat_number=booking_in.seat_number,
        status=models.BookingStatus.PENDING_PAYMENT
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    # 4. Call Payment Service (Fix: uses Dynamic Price)
    payment_success = False
    try:
        payment_payload = {
            "booking_id": db_booking.id,
            "user_id": db_booking.user_id,
            "amount": event_data.get("price", 100.0) 
        }
        # Note: Fixed URL as per Issue #3 (the router might not have /payments prefix but the base URL often does)
        payment_response = requests.post(PAYMENT_SERVICE_URL, json=payment_payload, timeout=2)
        
        if payment_response.status_code == 200:
            payment_success = True
            db_booking.status = models.BookingStatus.CONFIRMED
        else:
            db_booking.status = models.BookingStatus.EXPIRED
            
    except requests.exceptions.RequestException:
        print(f"WARNING: Payment Service at {PAYMENT_SERVICE_URL} unreachable.")
        # Issue #5: Never auto-confirm on failure. Keep as PENDING or set to EXPIRED.
        db_booking.status = models.BookingStatus.PENDING_PAYMENT 

    db.commit()
    db.refresh(db_booking)

    # 5. RabbitMQ Integration (Issue #4)
    if payment_success:
        rabbitmq.publish_booking_confirmed(
            booking_id=db_booking.id,
            user_id=db_booking.user_id,
            event_id=db_booking.event_id,
            event_name=event_data.get("name", "Unknown Event")
        )

    return db_booking

@router.get("/bookings/{user_id}", response_model=List[schemas.Booking])
def get_user_bookings(
    user_id: int, 
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(auth.get_current_user)
):
    # Security: Issue #6 - unauthorized user access check
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized: Cannot access other users' bookings")
        
    return db.query(models.Booking).filter(models.Booking.user_id == user_id).all()

@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: int, 
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(auth.get_current_user)
):
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Security: Issue #7 - unauthorized cancellation check
    if db_booking.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized: Cannot cancel other users' bookings")

    db_booking.status = models.BookingStatus.CANCELLED
    db.commit()
    return None
