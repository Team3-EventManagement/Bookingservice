# Booking Service

A microservice for managing event bookings, built with FastAPI, SQLAlchemy, and MySQL.

## Features
- Create bookings (integrates with Event and Payment services)
- View bookings for a specific user
- Cancel/Delete bookings

## Setup

### Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables (optional):
   - `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_DB`
3. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Compose (Recommended)
This will start both the Booking Service and a MySQL database:
```bash
docker-compose up --build
```

### Docker (Manual)
```bash
docker build -t booking-service .
docker run -p 8000:8000 booking-service
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment_and_service.yaml
```

## API Endpoints
- `POST /bookings`: Create a booking
- `GET /bookings/{user_id}`: Retrieve user bookings
- `DELETE /bookings/{booking_id}`: Cancel a booking
