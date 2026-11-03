"""Infrastructure implementation of the application ticket port."""

import hashlib

from app.domain.exceptions import TicketError
from app.domain.models import TicketImage, Trip
from app.infrastructure.browser.provider import BrowserProvider
from app.infrastructure.scraper.flows.workflows import (
    BuyTicketsFlow,
    GetTicketsFlow,
    LoginFlow,
)


class ItlaGateway:
    """Bound all browser workflows and avoid purchase retries."""

    def __init__(self, provider: BrowserProvider) -> None:
        self.provider = provider
        self.active_buyers: set[str] = set()

    async def login(self, username: str, password: str) -> bool:
        """Validate credentials in a new isolated session."""
        async with self.provider.session(), self.provider.context() as context:
            page = await context.new_page()
            return await LoginFlow().run(page, username, password)

    async def buy(
        self, username: str, password: str, trips: tuple[Trip, ...]
    ) -> list[TicketImage]:
        """Execute one purchase attempt for each requested trip."""
        account = hashlib.sha256(username.strip().lower().encode()).hexdigest()
        if account in self.active_buyers:
            raise TicketError(
                "PURCHASE_IN_PROGRESS",
                "A purchase is already in progress.",
                409,
            )
        self.active_buyers.add(account)
        try:
            async with self.provider.session():
                return await BuyTicketsFlow(self.provider).run(
                    username, password, trips
                )
        finally:
            self.active_buyers.discard(account)

    async def retrieve(
        self, username: str, password: str
    ) -> list[TicketImage]:
        """Retrieve tickets without creating or paying reservations."""
        async with self.provider.session():
            return await GetTicketsFlow(self.provider).run(username, password)
