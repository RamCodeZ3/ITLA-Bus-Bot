from pydantic import BaseModel


class TicketSchema(BaseModel):
    date: str
    arrival_route: str
    pickup_stop: str
    departure_route: str
