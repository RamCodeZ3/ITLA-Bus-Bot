"""Shared API fakes that never contact Campus Virtual."""

import struct
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


@pytest.fixture
def png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + struct.pack(">II", 120, 120)
        + b"\x08\x02\x00\x00\x00\x00\x00\x00\x00"
    )


@pytest.fixture
def gateway():
    return AsyncMock(
        login=AsyncMock(return_value=True),
        buy=AsyncMock(return_value=[]),
        retrieve=AsyncMock(return_value=[]),
    )


@pytest.fixture
def app(gateway):
    provider = AsyncMock(healthy=AsyncMock(return_value=True))
    settings = Settings(
        api_key=SecretStr("test-api-key-value"), _env_file=None
    )
    return create_app(settings, gateway=gateway, provider=provider)
