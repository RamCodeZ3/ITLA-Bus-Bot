import os
import unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from infrastructure.scraper.browser import lightpanda_context
from infrastructure.scraper.scrapper_ticket import ITLAScraper
from schemas.ticket_schema import TicketSchema
from utils.responses import error, ok


class ScraperFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scraper = ITLAScraper(
            1,
            TicketSchema(
                date="2026-11-02",
                arrival_route="arrival",
                pickup_stop="stop",
                departure_route="departure",
            ),
            "test@example.invalid",
            "test",
        )
        self.context = AsyncMock()

        @asynccontextmanager
        async def context():
            try:
                yield self.context
            finally:
                await self.context.close()

        self.connection = patch(
            "infrastructure.scraper.scrapper_ticket.lightpanda_context",
            context,
        )
        self.connection.start()
        self.addCleanup(self.connection.stop)
        for name in (
            "login", "go_to_transport", "fill_form", "confirm_reserve",
            "go_to_reserve_page", "confirm_buy",
        ):
            setattr(self.scraper, name, AsyncMock(return_value=ok()))
        self.scraper.balance_verification = AsyncMock(return_value=ok(100))

    async def test_login_failure_stops_before_reserving(self):
        self.scraper.login.return_value = error("login failed")
        result = await self.scraper.run()
        self.assertFalse(result["success"])
        self.scraper.go_to_transport.assert_not_awaited()
        self.scraper.confirm_buy.assert_not_awaited()
        self.context.close.assert_awaited_once()

    async def test_reservations_navigation_failure_stops_before_purchase(self):
        self.scraper.go_to_reserve_page.return_value = error("navigation")
        result = await self.scraper.run()
        self.assertEqual(result["error"], "navigation")
        self.scraper.confirm_buy.assert_not_awaited()
        self.context.close.assert_awaited_once()

    async def test_unexpected_failure_closes_session(self):
        self.scraper.fill_form.side_effect = RuntimeError("disconnected")
        with self.assertRaisesRegex(RuntimeError, "disconnected"):
            await self.scraper.run()
        self.scraper.confirm_reserve.assert_not_awaited()
        self.context.close.assert_awaited_once()


@unittest.skipUnless(
    os.getenv("LIGHTPANDA_INTEGRATION") == "1",
    "Set LIGHTPANDA_INTEGRATION=1 with a running Lightpanda CDP server",
)
class LightpandaIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_isolated_context_and_form_interaction(self):
        async with lightpanda_context() as context:
            page = await context.new_page()
            await page.goto(
                'data:text/html,<input id="email"><input type="radio" '
                'id="trip"><button onclick="document.body.dataset.saved='
                "document.querySelector('input').value\">Reservar</button>"
            )
            await page.locator("#email").fill("test@example.invalid")
            await page.locator("#trip").check()
            await page.get_by_role("button", name="Reservar").click()
            self.assertTrue(await page.locator("#trip").is_checked())
            self.assertEqual(
                await page.locator("body").get_attribute("data-saved"),
                "test@example.invalid",
            )


if __name__ == "__main__":
    unittest.main()
