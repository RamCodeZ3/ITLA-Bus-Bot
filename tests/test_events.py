"""Test request/reply lifecycle, failures and secret exclusion."""

import asyncio

import pytest
from pydantic import SecretStr

from app.application.event_bus import EventBus, ReplyRegistry, RequestState
from app.application.handlers import WorkflowHandlers
from app.domain.events import LoginValidationRequested, TicketPurchaseRequested
from app.domain.exceptions import TicketError


async def test_success_and_cleanup(gateway):
    bus = EventBus()
    replies = ReplyRegistry(bus)
    WorkflowHandlers(bus, replies, gateway)
    event = LoginValidationRequested(correlation_id="one")
    state = RequestState("student", SecretStr("private-password"))
    assert "private-password" not in repr(state)
    assert "student" not in repr(event)
    assert await replies.request(event, state, 1) is True
    assert not replies.states
    assert not replies.futures
    assert not replies.tasks


async def test_invalid_credentials_becomes_failure_reply(gateway):
    gateway.login.return_value = False
    bus = EventBus()
    replies = ReplyRegistry(bus)
    WorkflowHandlers(bus, replies, gateway)
    with pytest.raises(TicketError) as caught:
        await replies.request(
            LoginValidationRequested(correlation_id="invalid"),
            RequestState("user", SecretStr("private-password")),
            1,
        )
    assert caught.value.status == 401
    assert not replies.states


async def test_unknown_gateway_exception_is_redacted(gateway):
    gateway.buy.side_effect = RuntimeError("private-password")
    bus = EventBus()
    replies = ReplyRegistry(bus)
    WorkflowHandlers(bus, replies, gateway)
    with pytest.raises(TicketError) as caught:
        await replies.request(
            TicketPurchaseRequested(correlation_id="purchase"),
            RequestState("user", SecretStr("private-password")),
            1,
        )
    assert "private-password" not in str(caught.value)
    gateway.buy.assert_awaited_once()


async def test_timeout_cancels_work_and_discards_credentials(gateway):
    stopped = asyncio.Event()

    async def slow(*args):
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    gateway.buy.side_effect = slow
    bus = EventBus()
    replies = ReplyRegistry(bus)
    WorkflowHandlers(bus, replies, gateway)
    with pytest.raises(TicketError) as caught:
        await replies.request(
            TicketPurchaseRequested(correlation_id="slow"),
            RequestState("user", SecretStr("private-password")),
            0.01,
        )
    assert caught.value.status == 504
    assert stopped.is_set()
    assert not replies.states
    assert not replies.futures
    assert not replies.tasks


async def test_caller_cancellation_discards_state(gateway):
    entered = asyncio.Event()

    async def slow(*args):
        entered.set()
        await asyncio.Event().wait()

    gateway.buy.side_effect = slow
    bus = EventBus()
    replies = ReplyRegistry(bus)
    WorkflowHandlers(bus, replies, gateway)
    task = asyncio.create_task(
        replies.request(
            TicketPurchaseRequested(correlation_id="cancel"),
            RequestState("user", SecretStr("secret")),
            30,
        )
    )
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not replies.states
    assert not replies.tasks
