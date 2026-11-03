"""Opt-in browser checks without Campus credentials or paid actions."""

import asyncio
import base64
import os
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.infrastructure.browser.provider import BrowserProvider
from app.infrastructure.scraper.pages.reservations import (
    CAPTURE_IMAGES,
    validate_image,
)

pytestmark = pytest.mark.live


@pytest.mark.parametrize("engine", ["lightpanda", "chromium"])
async def test_real_context_isolation_and_health(engine):
    settings = Settings(
        api_key=SecretStr("test-browser-api-key"),
        browser_engine=engine,
        lightpanda_path=os.environ.get(
            "TEST_LIGHTPANDA_PATH", "/usr/local/bin/lightpanda"
        ),
        lightpanda_port=19333,
        _env_file=None,
    )
    provider = BrowserProvider(settings)
    try:
        await provider.start()
        assert await provider.healthy()
        async with provider.context() as first:
            await first.add_cookies(
                [
                    {
                        "name": "session",
                        "value": "private-user",
                        "domain": "example.com",
                        "path": "/",
                    }
                ]
            )
        async with provider.context() as second:
            assert not await second.cookies()
            page = await second.new_page()
            await page.goto('data:text/html,<input id="email">')
            await page.locator("#email").fill("student")
            assert await page.locator("#email").input_value() == "student"
        if engine == "lightpanda":
            provider.process.kill()
            await provider.process.wait()
            # Force the CDP disconnection callback to run before reconnecting.
            for _ in range(50):
                if not provider.browser.is_connected():
                    break
                await asyncio.sleep(0.01)
            async with provider.context() as recovered:
                assert await recovered.new_page()
            assert await provider.healthy()
    finally:
        await provider.close()


@pytest.mark.parametrize("kind", ["data", "blob", "detached-dispatch"])
async def test_canvas_capture_never_downloads_to_disk(kind):
    settings = Settings(
        api_key=SecretStr("test-browser-api-key"),
        browser_engine="chromium",
        _env_file=None,
    )
    provider = BrowserProvider(settings)
    try:
        await provider.start()
        async with provider.context(rendering=True) as context:
            await context.add_init_script(CAPTURE_IMAGES)
            page = await context.new_page()
            downloads = AsyncMock()
            page.on("download", downloads)
            await page.goto("data:text/html,<canvas width='120' height='120'>")
            await page.evaluate(
                """kind => {
                const canvas = document.querySelector('canvas');
                canvas.getContext('2d').fillRect(0, 0, 120, 120);
                const anchor = document.createElement('a');
                anchor.download = 'ticket.png';
                if (kind === 'blob' || kind === 'detached-dispatch') {
                    canvas.toBlob(blob => {
                        anchor.href = URL.createObjectURL(blob);
                        if (kind === 'detached-dispatch') {
                            anchor.dispatchEvent(new MouseEvent('click'));
                        } else { anchor.click(); }
                        URL.revokeObjectURL(anchor.href);
                    }, 'image/png');
                } else {
                    anchor.href = canvas.toDataURL('image/png');
                    anchor.click();
                }
            }""",
                kind,
            )
            await page.wait_for_function("window.__ticketImages.length > 0")
            encoded = await page.evaluate("window.__ticketImages[0]")
            validate_image(base64.b64decode(encoded.split(",", 1)[1]))
            downloads.assert_not_called()
    finally:
        await provider.close()
