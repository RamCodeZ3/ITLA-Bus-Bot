"""Authenticated HTTP producers for application events."""

import base64
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import APIKeyHeader

from app.application.event_bus import RequestState
from app.domain.events import (
    Event,
    LoginValidationRequested,
    TicketPurchaseRequested,
    TicketsRetrievalRequested,
)
from app.domain.exceptions import TicketError
from app.domain.models import Trip
from app.presentation.schemas import (
    Credentials,
    LoginResponse,
    PurchaseRequest,
    TicketResponse,
    TicketsResponse,
)
from app.routes_data import ROUTES_DATA

key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def authenticate(
    request: Request, key: Annotated[str | None, Depends(key_header)]
) -> None:
    """Compare the shared API key in constant time."""
    expected = request.app.state.settings.api_key.get_secret_value()
    if key is None or not secrets.compare_digest(
        key.encode(), expected.encode()
    ):
        raise TicketError("UNAUTHORIZED", "Invalid API key.", 401)


router = APIRouter(
    prefix="/api/v1/itla-tickets", dependencies=[Depends(authenticate)]
)


async def execute(
    request: Request, body: Credentials, event_type: type[Event]
) -> Any:
    """Publish a metadata-only event and await its correlated reply."""
    trips = ()
    if isinstance(body, PurchaseRequest):
        trips = tuple(Trip(**trip.model_dump()) for trip in body.trips)
    state = RequestState(body.username, body.password, trips)
    return await request.app.state.replies.request(
        event_type(correlation_id=request.state.correlation_id),
        state,
        request.app.state.settings.request_timeout,
    )


def encode_tickets(images: list) -> TicketsResponse:
    """Encode byte payloads only at the HTTP boundary."""
    return TicketsResponse(
        tickets=[
            TicketResponse(
                id=image.id,
                filename=image.filename,
                content_type=image.content_type,
                data_base64=base64.b64encode(image.data).decode("ascii"),
            )
            for image in images
        ]
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: Credentials) -> LoginResponse:
    """Validate Campus credentials without creating a reusable session."""
    await execute(request, body, LoginValidationRequested)
    return LoginResponse(valid=True)


@router.post("/buy-tickets", response_model=TicketsResponse)
async def buy_tickets(
    request: Request, body: PurchaseRequest
) -> TicketsResponse:
    """Purchase requested round trips once and return image data."""
    return encode_tickets(
        await execute(request, body, TicketPurchaseRequested)
    )


@router.post("/get-tickets", response_model=TicketsResponse)
async def get_tickets(request: Request, body: Credentials) -> TicketsResponse:
    """Retrieve purchased tickets without performing another payment."""
    return encode_tickets(
        await execute(request, body, TicketsRetrievalRequested)
    )


@router.get("/routes")
async def routes() -> dict:
    """Return the shared weekday and Saturday validation catalog."""
    return ROUTES_DATA
