"""Transport home and reservation form."""

import unicodedata
from decimal import Decimal

from app.domain.exceptions import TicketError
from app.domain.models import Trip
from app.infrastructure.scraper.pages.base import BasePage


class TransportPage(BasePage):
    """Verify credit and reserve the requested route pair."""

    async def verify_balance(self, ticket_count: int) -> None:
        """Retain the existing RD$30 per direction balance check."""
        text = await self.page.locator("span", has_text="DOP").inner_text()
        balance = Decimal(text.replace("DOP", "").replace(",", "").strip())
        if balance < Decimal(30) * ticket_count:
            raise TicketError(
                "INSUFFICIENT_BALANCE", "Insufficient Campus balance.", 409
            )

    async def reserve(self, trip: Trip) -> None:
        """Select exact catalog values and submit one round-trip request."""
        await self.page.locator("client-ticket-reserve").wait_for()
        await self.page.locator("#reserve_date").wait_for()
        await self.page.locator("#EntradaySalida").check()
        await self.page.locator("#reserve_date").fill(trip.date.isoformat())
        await self._select("time_in", trip.arrival_route)
        await self._select("stop_in", trip.pickup_stop)
        await self._select("time_out", trip.departure_route)
        await self._select("stop_out", None)
        await self.page.get_by_role(
            "button", name="Reservar", exact=True
        ).click()

    async def _select(self, field: str, value: str | None) -> None:
        dropdown = self.page.locator(f"ngx-select-dropdown#{field}")
        await dropdown.locator(".ngx-dropdown-button").click()
        options = dropdown.locator(".available-item")
        await options.first.wait_for()
        count = await options.count()
        if count == 1:
            await options.first.click()
            return
        if value is not None:
            matches = []
            for index in range(count):
                if self._normalize(value) in self._normalize(
                    await options.nth(index).inner_text()
                ):
                    matches.append(index)
            if len(matches) == 1:
                await options.nth(matches[0]).click()
                return
        raise TicketError(
            "ROUTE_UNAVAILABLE",
            "Requested route or stop is unavailable or ambiguous.",
            409,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return (
            unicodedata.normalize("NFD", value)
            .encode("ascii", "ignore")
            .decode()
            .strip()
            .lower()
        )
