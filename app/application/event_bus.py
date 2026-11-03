"""Async request/reply bus with request-scoped private payloads."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import SecretStr

from app.domain.events import Event
from app.domain.exceptions import TicketError
from app.domain.models import Trip

logger = logging.getLogger(__name__)
type Listener = Callable[[Event], Awaitable[None]]


@dataclass
class RequestState:
    """Private state discarded when a request finishes or is cancelled."""

    username: str = field(repr=False)
    password: SecretStr = field(repr=False)
    trips: tuple[Trip, ...] = ()
    result: Any = field(default=None, repr=False)
    error: TicketError | None = None


class EventBus:
    """Dispatch typed events without retaining event history."""

    def __init__(self) -> None:
        self.listeners: dict[type[Event], list[Listener]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], listener: Listener) -> None:
        """Register an asynchronous consumer."""
        self.listeners[event_type].append(listener)

    async def publish(self, event: Event) -> None:
        """Deliver an event to all listeners of its concrete type."""
        logger.info(
            "event=%s correlation_id=%s",
            type(event).__name__,
            event.correlation_id,
        )
        for listener in self.listeners[type(event)]:
            await listener(event)


class ReplyRegistry:
    """Resolve futures using metadata-only completion events."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.states: dict[str, RequestState] = {}
        self.futures: dict[str, asyncio.Future[Any]] = {}
        self.tasks: set[asyncio.Task[None]] = set()

    async def resolve(self, event: Event) -> None:
        """Resolve a registered reply from its private request state."""
        future = self.futures.get(event.correlation_id)
        state = self.states.get(event.correlation_id)
        if future is not None and state is not None and not future.done():
            if state.error:
                future.set_exception(state.error)
            else:
                future.set_result(state.result)

    async def request(
        self, event: Event, state: RequestState, deadline_seconds: float
    ) -> Any:
        """Await a reply and always release credentials and images."""
        key = event.correlation_id
        if key in self.states:
            raise TicketError("REQUEST_CONFLICT", "Request is active.", 409)
        future = asyncio.get_running_loop().create_future()
        self.states[key] = state
        self.futures[key] = future
        task = asyncio.create_task(self.bus.publish(event))
        self.tasks.add(task)
        try:
            async with asyncio.timeout(deadline_seconds):
                return await future
        except TimeoutError:
            raise TicketError(
                "WORKFLOW_TIMEOUT",
                "Outcome may be unknown. Retrieve tickets before retrying.",
                504,
            ) from None
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self.tasks.discard(task)
            self.states.pop(key, None)
            self.futures.pop(key, None)
            if not future.done():
                future.cancel()

    async def close(self) -> None:
        """Cancel in-flight work during application shutdown."""
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for future in self.futures.values():
            if not future.done():
                future.cancel()
        self.states.clear()
        self.futures.clear()
        self.tasks.clear()
