"""Authenticated Campus Virtual home page."""

from app.infrastructure.scraper.pages.base import BasePage


class CampusPage(BasePage):
    """Navigate from the Campus session to the transport application."""

    async def open_transport(self) -> None:
        """Follow the existing transport link and verify its destination."""
        await self.page.locator("li.pointer a", has_text="Transporte").click()
        await self.page.wait_for_url("**/customers/home**")
        await self.page.wait_for_load_state("domcontentloaded")
