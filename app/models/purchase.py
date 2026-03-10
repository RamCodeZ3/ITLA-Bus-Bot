from pydantic import BaseModel
from typing import Optional
from datetime import date


class Purchase(BaseModel):
    user_id: int
    date: date
    ticket_type: str
    arrival_route: Optional[str] = None
    pickup_stop: Optional[str] = None
    departure_route: Optional[str] = None
    dropoff_stop: Optional[str] = None

