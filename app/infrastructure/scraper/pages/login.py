"""Campus Virtual login page."""

import re

from app.domain.exceptions import TicketError
from app.infrastructure.scraper.pages.base import BasePage


class LoginPage(BasePage):
    """Preserve explicit authenticated and rejected login checks."""

    _URL = "https://campusvirtual.itla.edu.do/account/login"
    _AUTHENTICATED = (
        ".btn-logout:visible, button:has-text('Salir'):visible, "
        "li.pointer a:has-text('Transporte'):visible"
    )
    _REJECTED = (
        ".alert-danger:visible, .error-msg:visible, "
        ".invalid-feedback:visible, .text-danger:visible"
    )

    async def login(self, username: str, password: str) -> None:
        """Submit credentials and require a visible outcome."""
        await self.navigate(self._URL)
        await self.page.locator("#email").fill(username)
        await self.page.locator("#password").fill(password)
        await self.page.get_by_role("button", name="Iniciar Sesión").click()
        authenticated = self.page.locator(self._AUTHENTICATED)
        rejected = self.page.locator(self._REJECTED).filter(
            has_text=re.compile(r"\S")
        )
        await authenticated.or_(rejected).first.wait_for(state="visible")
        if not await authenticated.count():
            raise TicketError(
                "INVALID_CREDENTIALS", "Invalid credentials.", 401
            )
