"""Explicit account-based verification; purchases need a second opt-in."""

import json
import os

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.domain.models import Trip
from app.infrastructure.browser.provider import BrowserProvider
from app.infrastructure.scraper.gateway import ItlaGateway
from app.presentation.schemas import TripRequest

pytestmark = pytest.mark.live


@pytest.fixture
async def campus_gateway():
    username = os.environ.get("CAMPUS_TEST_USERNAME")
    password = os.environ.get("CAMPUS_TEST_PASSWORD")
    if not username or not password:
        pytest.skip("Explicit Campus test credentials are required")
    provider = BrowserProvider(
        Settings(
            api_key=SecretStr("campus-local-test-key"),
            browser_engine=os.environ.get("TEST_BROWSER_ENGINE", "lightpanda"),
            lightpanda_path=os.environ.get(
                "TEST_LIGHTPANDA_PATH", "/usr/local/bin/lightpanda"
            ),
            lightpanda_port=19335,
            _env_file=None,
        )
    )
    try:
        await provider.start()
        yield ItlaGateway(provider), username, password
    finally:
        await provider.close()


async def test_campus_login(campus_gateway):
    gateway, username, password = campus_gateway
    assert await gateway.login(username, password)


async def test_campus_retrieval_without_purchase(campus_gateway):
    gateway, username, password = campus_gateway
    tickets = await gateway.retrieve(username, password)
    assert isinstance(tickets, list)


async def test_campus_purchase_explicit_opt_in(campus_gateway):
    if os.environ.get("CAMPUS_ALLOW_PURCHASE") != "1":
        pytest.skip("Set CAMPUS_ALLOW_PURCHASE=1 to authorize a real payment")
    raw = os.environ.get("CAMPUS_TEST_TRIP_JSON")
    if not raw:
        pytest.skip("A concrete catalog-valid trip is required")
    trip = TripRequest.model_validate(json.loads(raw))
    gateway, username, password = campus_gateway
    tickets = await gateway.buy(
        username, password, (Trip(**trip.model_dump()),)
    )
    assert isinstance(tickets, list)
