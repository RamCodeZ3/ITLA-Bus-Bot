"""Shared page behavior without business orchestration."""

from playwright.async_api import Page

from app.domain.exceptions import TicketError


class BasePage:
    """Provide explicit navigation and in-memory diagnostics."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def navigate(self, url: str) -> None:
        """Navigate and reject HTTP failures without leaking page content."""
        response = await self.page.goto(url, wait_until="domcontentloaded")
        if response and response.status >= 400:
            raise TicketError(
                "CAMPUS_UNAVAILABLE", "Campus is unavailable.", 503
            )

    async def screenshot(self) -> bytes:
        """Capture diagnostics in memory only when the engine supports it."""
        return await self.page.screenshot(type="png")
