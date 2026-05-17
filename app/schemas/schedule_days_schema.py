from pydantic import BaseModel


class ScheduleDaysSchema(BaseModel):
    schedule_id: int
    day: str
    ticket_type: str
    arrival_route: str | None = None
    pickup_stop: str | None = None
    departure_route: str | None = None
