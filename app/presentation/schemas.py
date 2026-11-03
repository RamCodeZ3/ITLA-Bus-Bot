"""Strict public contracts aligned with the existing route catalog."""

import datetime
import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.routes_data import ROUTES_DATA


class Credentials(BaseModel):
    """Credentials supplied anew on every request."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    username: str = Field(min_length=1, max_length=254, repr=False)
    password: SecretStr = Field(min_length=1, max_length=4096, repr=False)


class TripRequest(BaseModel):
    """A round trip using the portal's complete route labels."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    date: datetime.date
    arrival_route: str = Field(min_length=1, max_length=256)
    pickup_stop: str = Field(min_length=1, max_length=512)
    departure_route: str = Field(min_length=1, max_length=256)

    @model_validator(mode="before")
    @classmethod
    def require_iso_date(cls, value: dict) -> dict:
        """Require calendar dates, rejecting Unix timestamps and datetimes."""
        day = value.get("date") if isinstance(value, dict) else None
        if not isinstance(day, datetime.date) and (
            not isinstance(day, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
        ):
            raise ValueError("date must use YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        """Validate route direction, weekday and route-specific stop."""
        if self.date.weekday() == 6:
            raise ValueError("Sunday trips are not supported")
        catalog = ROUTES_DATA[
            "saturday" if self.date.weekday() == 5 else "weekday"
        ]
        if self.arrival_route not in catalog["arrival"]["routes"]:
            raise ValueError("Invalid arrival route for the selected day")
        if self.departure_route not in catalog["departure"]["routes"]:
            raise ValueError("Invalid departure route for the selected day")
        stops = catalog["arrival"]["stops_by_route"].get(
            self.arrival_route, []
        )
        if self.pickup_stop not in (stops or ["Única parada"]):
            raise ValueError("Invalid pickup stop for the arrival route")
        return self


class PurchaseRequest(Credentials):
    """Concrete trips held by the consumer device."""

    trips: list[TripRequest] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def distinct_dates(self) -> Self:
        """Prevent ambiguous duplicate reservations within a request."""
        if len({trip.date for trip in self.trips}) != len(self.trips):
            raise ValueError("Only one round trip per date is supported")
        return self


class TicketResponse(BaseModel):
    """A ticket returned as an in-memory base64 image."""

    id: str
    filename: str
    content_type: str
    data_base64: str


class TicketsResponse(BaseModel):
    """Images retrieved or generated after a confirmed purchase."""

    tickets: list[TicketResponse]


class LoginResponse(BaseModel):
    """Successful credential validation without a retained session."""

    valid: bool
