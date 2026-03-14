from fastapi import FastAPI
from . import models, routes
from .database import engine

# Create tables on startup (if they don't exist)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Booking Service", version="1.0.0")

app.include_router(routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Booking Service"}
