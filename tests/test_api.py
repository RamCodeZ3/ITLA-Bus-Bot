"""HTTP contracts exercised with fake browser workflows."""

import base64

import httpx
import pytest

from app.domain.exceptions import TicketError
from app.domain.models import TicketImage
from app.routes_data import ROUTES_DATA

PREFIX = "/api/v1/itla-tickets"
AUTH = {"X-API-Key": "test-api-key-value"}
CREDENTIALS = {
    "username": "student@example.invalid",
    "password": "private-pass",
}


@pytest.fixture
async def client(app):
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        yield client


async def test_auth_required(client, gateway):
    response = await client.post(f"{PREFIX}/login", json=CREDENTIALS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    gateway.login.assert_not_called()


async def test_login_and_no_cache(client, gateway):
    response = await client.post(
        f"{PREFIX}/login", headers=AUTH, json=CREDENTIALS
    )
    assert response.json() == {"valid": True}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Correlation-ID"]
    gateway.login.assert_awaited_once()


async def test_login_rejection(client, gateway):
    gateway.login.side_effect = TicketError(
        "INVALID_CREDENTIALS", "Invalid credentials.", 401
    )
    response = await client.post(
        f"{PREFIX}/login", headers=AUTH, json=CREDENTIALS
    )
    assert response.status_code == 401
    assert response.json()["error"]["correlation_id"]
    assert "private-pass" not in response.text


async def test_images_are_base64(client, gateway, png):
    gateway.retrieve.return_value = [TicketImage("entry", "entry.png", png)]
    response = await client.post(
        f"{PREFIX}/get-tickets", headers=AUTH, json=CREDENTIALS
    )
    assert response.status_code == 200
    image = response.json()["tickets"][0]
    assert base64.b64decode(image["data_base64"]) == png
    assert image["content_type"] == "image/png"


async def test_empty_retrieval(client):
    response = await client.post(
        f"{PREFIX}/get-tickets", headers=AUTH, json=CREDENTIALS
    )
    assert response.json() == {"tickets": []}


def valid_trip():
    arrival = ROUTES_DATA["weekday"]["arrival"]
    route = arrival["routes"][0]
    return {
        "date": "2026-11-04",
        "arrival_route": route,
        "pickup_stop": arrival["stops_by_route"][route][0],
        "departure_route": ROUTES_DATA["weekday"]["departure"]["routes"][0],
    }


async def test_purchase_passes_concrete_inputs(client, gateway):
    response = await client.post(
        f"{PREFIX}/buy-tickets",
        headers=AUTH,
        json={
            **CREDENTIALS,
            "trips": [valid_trip()],
        },
    )
    assert response.status_code == 200
    gateway.buy.assert_awaited_once()
    assert (
        gateway.buy.call_args.args[2][0].arrival_route
        == (valid_trip()["arrival_route"])
    )


@pytest.mark.parametrize(
    "change",
    [
        {"pickup_stop": "invalid"},
        {"arrival_route": "invalid"},
        {"departure_route": "invalid"},
        {"date": "2026-11-08"},
        {"date": 1793740000},
    ],
)
async def test_invalid_trip_never_buys(client, gateway, change):
    response = await client.post(
        f"{PREFIX}/buy-tickets",
        headers=AUTH,
        json={
            **CREDENTIALS,
            "trips": [{**valid_trip(), **change}],
        },
    )
    assert response.status_code == 422
    assert "private-pass" not in response.text
    gateway.buy.assert_not_called()


async def test_validation_does_not_echo_secrets(client):
    response = await client.post(
        f"{PREFIX}/login",
        headers=AUTH,
        json={
            "username": "student",
            "password": {"secret": "private-pass"},
        },
    )
    assert response.status_code == 422
    assert "private-pass" not in response.text


async def test_routes_and_health(client):
    assert (await client.get(f"{PREFIX}/routes", headers=AUTH)).json() == (
        ROUTES_DATA
    )
    assert (await client.get("/health")).json()["browser_ready"] is True


@pytest.mark.parametrize("status", [409, 502, 503, 504])
async def test_domain_error_envelope(client, gateway, status):
    gateway.retrieve.side_effect = TicketError(
        "SAFE_FAILURE", "Safe workflow failure.", status
    )
    response = await client.post(
        f"{PREFIX}/get-tickets", headers=AUTH, json=CREDENTIALS
    )
    assert response.status_code == status
    error = response.json()["error"]
    assert set(error) == {"code", "message", "correlation_id"}
    assert error["correlation_id"] == response.headers["X-Correlation-ID"]


async def test_health_unavailable(app):
    # The public route captures its provider; test readiness separately through
    # a provider fake on a new app to avoid exposing implementation state.
    from unittest.mock import AsyncMock

    from app.main import create_app

    unready = create_app(
        app.state.settings,
        gateway=AsyncMock(),
        provider=AsyncMock(healthy=AsyncMock(return_value=False)),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=unready), base_url="http://test"
    ) as probe:
        response = await probe.get("/health")
    assert response.status_code == 503
    assert response.json()["browser_ready"] is False
