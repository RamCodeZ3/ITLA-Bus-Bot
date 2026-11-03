"""Application handlers that translate every failure into a reply event."""

import logging

from app.application.event_bus import EventBus, ReplyRegistry
from app.application.ports import TicketGateway
from app.domain.events import (
    Event,
    LoginValidated,
    LoginValidationFailed,
    LoginValidationRequested,
    TicketPurchaseFailed,
    TicketPurchaseRequested,
    TicketsPurchased,
    TicketsRetrievalFailed,
    TicketsRetrievalRequested,
    TicketsRetrieved,
)
from app.domain.exceptions import TicketError

logger = logging.getLogger(__name__)


class WorkflowHandlers:
    """Subscribe workflows and keep secrets outside event payloads."""

    def __init__(
        self, bus: EventBus, replies: ReplyRegistry, gateway: TicketGateway
    ) -> None:
        self.bus = bus
        self.replies = replies
        self.gateway = gateway
        for event_type in (
            LoginValidationRequested,
            TicketPurchaseRequested,
            TicketsRetrievalRequested,
        ):
            bus.subscribe(event_type, self.handle)
        for event_type in (
            LoginValidated,
            LoginValidationFailed,
            TicketsPurchased,
            TicketPurchaseFailed,
            TicketsRetrieved,
            TicketsRetrievalFailed,
        ):
            bus.subscribe(event_type, replies.resolve)

    async def handle(self, event: Event) -> None:
        """Execute once; publish a safe completion or failure event."""
        state = self.replies.states[event.correlation_id]
        success, failure = {
            LoginValidationRequested: (LoginValidated, LoginValidationFailed),
            TicketPurchaseRequested: (TicketsPurchased, TicketPurchaseFailed),
            TicketsRetrievalRequested: (
                TicketsRetrieved,
                TicketsRetrievalFailed,
            ),
        }[type(event)]
        reply = success
        try:
            password = state.password.get_secret_value()
            if isinstance(event, LoginValidationRequested):
                state.result = await self.gateway.login(
                    state.username, password
                )
                if not state.result:
                    raise TicketError(
                        "INVALID_CREDENTIALS", "Invalid credentials.", 401
                    )
            elif isinstance(event, TicketPurchaseRequested):
                state.result = await self.gateway.buy(
                    state.username, password, state.trips
                )
            else:
                state.result = await self.gateway.retrieve(
                    state.username, password
                )
        except TicketError as exc:
            state.error = exc
            reply = failure
        except Exception:
            state.error = TicketError(
                "UPSTREAM_FAILURE",
                "Campus workflow failed. Retrieve tickets before retrying.",
            )
            reply = failure
        if state.error:
            logger.warning(
                "workflow_failed code=%s correlation_id=%s",
                state.error.code,
                event.correlation_id,
            )
        await self.bus.publish(reply(correlation_id=event.correlation_id))
