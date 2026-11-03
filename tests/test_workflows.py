"""Verify purchase safety and workflow context cleanup."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.exceptions import TicketError
from app.domain.models import Trip
from app.infrastructure.scraper.flows.workflows import BuyTicketsFlow
from app.infrastructure.scraper.gateway import ItlaGateway
from app.infrastructure.scraper.pages.reservations import ReservationsPage

TRIPS = (Trip(date(2026, 11, 4), "arrival", "stop", "departure"),)


def provider_fake():
    provider = MagicMock()
    context = MagicMock(new_page=AsyncMock(return_value=MagicMock()))
    context.close = AsyncMock()

    @asynccontextmanager
    async def isolated(**kwargs):
        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def session():
        yield

    provider.context = isolated
    provider.session = session
    return provider, context


async def test_image_failure_after_payment_does_not_retry():
    provider, context = provider_fake()
    with (
        patch("app.infrastructure.scraper.flows.workflows.LoginFlow") as login,
        patch(
            "app.infrastructure.scraper.flows.workflows.CampusPage"
        ) as campus,
        patch(
            "app.infrastructure.scraper.flows.workflows.TransportPage"
        ) as transport,
        patch(
            "app.infrastructure.scraper.flows.workflows.ReservationsPage"
        ) as reservations,
        patch(
            "app.infrastructure.scraper.flows.workflows.GetTicketsFlow"
        ) as images,
    ):
        login.return_value.run = AsyncMock()
        campus.return_value.open_transport = AsyncMock()
        for method in ("verify_balance", "navigate", "reserve"):
            setattr(transport.return_value, method, AsyncMock())
        for method in ("open", "assert_not_reserved", "purchase"):
            setattr(reservations.return_value, method, AsyncMock())
        images.return_value.run = AsyncMock(side_effect=RuntimeError("canvas"))
        result = await BuyTicketsFlow(provider).run("student", "secret", TRIPS)
        assert result == []
        reservations.return_value.purchase.assert_awaited_once()
        context.close.assert_awaited_once()


async def test_duplicate_active_account_is_rejected():
    provider, _ = provider_fake()
    gateway = ItlaGateway(provider)
    entered = asyncio.Event()
    finish = asyncio.Event()

    async def buy(*args):
        entered.set()
        await finish.wait()
        return []

    with patch("app.infrastructure.scraper.gateway.BuyTicketsFlow") as flow:
        flow.return_value.run = buy
        task = asyncio.create_task(gateway.buy("student", "secret", TRIPS))
        await entered.wait()
        with pytest.raises(TicketError) as error:
            await gateway.buy("STUDENT", "secret", TRIPS)
        assert error.value.status == 409
        finish.set()
        await task
    assert not gateway.active_buyers


async def test_payment_timeout_is_unknown_and_never_retried():
    page = MagicMock()
    row = MagicMock()
    qr = MagicMock(count=AsyncMock(return_value=0))
    row.locator.side_effect = lambda selector: (
        qr if "plantilla-qr" in selector else MagicMock(click=AsyncMock())
    )
    confirmation = MagicMock(click=AsyncMock(side_effect=TimeoutError()))
    page.locator.side_effect = lambda selector: (
        confirmation
        if selector == "button.swal2-confirm"
        else MagicMock(wait_for=AsyncMock())
    )
    reservations = ReservationsPage(page)
    reservations.row_for_date = AsyncMock(return_value=row)
    with pytest.raises(TicketError) as error:
        await reservations.purchase(date(2026, 11, 4))
    assert error.value.code == "PURCHASE_OUTCOME_UNKNOWN"
    confirmation.click.assert_awaited_once()
