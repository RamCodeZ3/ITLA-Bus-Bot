"""Immutable automation inputs and outputs."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Trip:
    """A concrete round trip selected from the route catalog."""

    date: date
    arrival_route: str
    pickup_stop: str
    departure_route: str


@dataclass(frozen=True)
class TicketImage:
    """A validated ticket image held exclusively in memory."""

    id: str
    filename: str
    data: bytes = field(repr=False)
    content_type: str = "image/png"
