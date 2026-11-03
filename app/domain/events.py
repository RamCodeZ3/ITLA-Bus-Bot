"""Credential-free request and completion events."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, kw_only=True)
class Event:
    """Metadata shared by all workflow events."""

    correlation_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, kw_only=True)
class LoginValidationRequested(Event):
    """Request credential validation using the request-scoped input vault."""


@dataclass(frozen=True, kw_only=True)
class LoginValidated(Event):
    """Report a successful login validation."""


@dataclass(frozen=True, kw_only=True)
class LoginValidationFailed(Event):
    """Report a failed login validation."""


@dataclass(frozen=True, kw_only=True)
class TicketPurchaseRequested(Event):
    """Request a purchase using the request-scoped input vault."""


@dataclass(frozen=True, kw_only=True)
class TicketsPurchased(Event):
    """Report completion without embedding image bytes."""


@dataclass(frozen=True, kw_only=True)
class TicketPurchaseFailed(Event):
    """Report a failed or uncertain purchase."""


@dataclass(frozen=True, kw_only=True)
class TicketsRetrievalRequested(Event):
    """Request retrieval of existing tickets."""


@dataclass(frozen=True, kw_only=True)
class TicketsRetrieved(Event):
    """Report retrieval completion."""


@dataclass(frozen=True, kw_only=True)
class TicketsRetrievalFailed(Event):
    """Report retrieval failure."""
