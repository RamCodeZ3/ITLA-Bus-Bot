"""Interfaces implemented by browser infrastructure."""

from typing import Protocol

from app.domain.models import TicketImage, Trip


class TicketGateway(Protocol):
    """Expose the three isolated Campus workflows."""

    async def login(self, username: str, password: str) -> bool:
        """Validate credentials without retaining a session."""
        ...

    async def buy(
        self, username: str, password: str, trips: tuple[Trip, ...]
    ) -> list[TicketImage]:
        """Purchase round trips once and retrieve images."""
        ...

    async def retrieve(
        self, username: str, password: str
    ) -> list[TicketImage]:
        """Retrieve existing tickets without purchasing."""
        ...
