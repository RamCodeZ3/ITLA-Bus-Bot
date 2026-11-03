"""Compose real portal pages into request-scoped use cases."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.async_api import Page

from app.domain.exceptions import TicketError
from app.domain.models import TicketImage, Trip
from app.infrastructure.browser.provider import BrowserProvider
from app.infrastructure.scraper.pages.campus import CampusPage
from app.infrastructure.scraper.pages.login import LoginPage
from app.infrastructure.scraper.pages.reservations import (
    CAPTURE_IMAGES,
    ReservationsPage,
)
from app.infrastructure.scraper.pages.transport import TransportPage

logger = logging.getLogger(__name__)


class LoginFlow:
    """Validate credentials using the current DOM confirmation checks."""

    async def run(self, page: Page, username: str, password: str) -> bool:
        """Fail closed when the Campus never confirms login."""
        try:
            await LoginPage(page).login(username, password)
        except TicketError:
            raise
        except Exception:
            raise TicketError(
                "CAMPUS_UNAVAILABLE",
                "Campus login could not be confirmed.",
                503,
            ) from None
        return True


class GetTicketsFlow:
    """Use a rendering context only to retrieve already purchased tickets."""

    def __init__(self, provider: BrowserProvider) -> None:
        self.provider = provider

    async def run(
        self, username: str, password: str, days: tuple = ()
    ) -> list[TicketImage]:
        """Retrieve requested purchase dates or the first usable row."""
        async with self.provider.context(rendering=True) as context:
            await context.add_init_script(CAPTURE_IMAGES)
            page = await context.new_page()
            await LoginFlow().run(page, username, password)
            await CampusPage(page).open_transport()
            reservations = ReservationsPage(page)
            await reservations.open()
            if not days:
                today = datetime.now(ZoneInfo("America/Santo_Domingo")).date()
                day = await reservations.first_usable_date(today)
                if day is None:
                    return []
                days = (day,)
            images = []
            for day in days:
                images.extend(await reservations.images(day))
            return images


class BuyTicketsFlow:
    """Reserve and pay once, then recover images using a fresh context."""

    def __init__(self, provider: BrowserProvider) -> None:
        self.provider = provider

    async def run(
        self, username: str, password: str, trips: tuple[Trip, ...]
    ) -> list[TicketImage]:
        """Preflight all dates before starting any purchase."""
        async with self.provider.context() as context:
            page = await context.new_page()
            await LoginFlow().run(page, username, password)
            await CampusPage(page).open_transport()
            await TransportPage(page).verify_balance(len(trips) * 2)
            reservations = ReservationsPage(page)
            await reservations.open()
            for trip in trips:
                await reservations.assert_not_reserved(trip.date)
            for trip in trips:
                await TransportPage(page).navigate(
                    "https://transporte.itla.edu.do/customers/home"
                )
                await TransportPage(page).reserve(trip)
                await reservations.open()
                await reservations.purchase(trip.date)
        try:
            return await GetTicketsFlow(self.provider).run(
                username, password, tuple(trip.date for trip in trips)
            )
        except Exception:
            # All payments are confirmed. Image failure must not invite a buy.
            logger.warning("ticket_images_unavailable_after_confirmed_payment")
            return []
