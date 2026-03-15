from pydantic import BaseModel
from typing import Optional


class ScheduleDays(BaseModel):
    schedule_id: int
    day: str
    ticket_type: str
    arrival_route: Optional[str] = None
    pickup_stop: Optional[str] = None
    departure_route: Optional[str] = None
    dropoff_stop: Optional[str] = None
