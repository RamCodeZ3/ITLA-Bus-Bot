import os
from contextlib import asynccontextmanager

from playwright.async_api import Error, async_playwright


@asynccontextmanager
async def lightpanda_context():
    """Open an isolated session on the configured Lightpanda CDP server."""
    endpoint = os.getenv("LIGHTPANDA_CDP_URL", "ws://127.0.0.1:9222")
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.connect_over_cdp(
                endpoint, timeout=15000
            )
        except Error:
            # Do not expose endpoint credentials in error messages.
            raise RuntimeError(
                "No se pudo conectar a Lightpanda. Inicia 'lightpanda serve "
                "--host 127.0.0.1 --port 9222' o configura "
                "LIGHTPANDA_CDP_URL."
            ) from None

        try:
            context = await browser.new_context(accept_downloads=True)
            try:
                yield context
            finally:
                await context.close()
        finally:
            await browser.close()
