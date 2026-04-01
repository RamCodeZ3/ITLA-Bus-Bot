from pydantic import BaseModel


class TicketModel(BaseModel):
    date: str
    arrival_route: str
    pickup_stop: str
    departure_route: str