"""Long-lived browser processes and isolated, bounded request contexts."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from time import monotonic

from playwright.async_api import Browser, BrowserContext, async_playwright

from app.config import Settings
from app.domain.exceptions import TicketError


class BrowserProvider:
    """Own a CDP connection and a rendering fallback behind one interface."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process: asyncio.subprocess.Process | None = None
        self.browser: Browser | None = None
        self.renderer: Browser | None = None
        self.playwright = None
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_sessions)

    async def start(self) -> None:
        """Wait for browser readiness before accepting API traffic."""
        self.playwright = await async_playwright().start()
        try:
            await self._connect()
            if self.settings.browser_engine == "lightpanda":
                self.renderer = await self.playwright.chromium.launch(
                    headless=True
                )
        except BaseException:
            await self.close()
            raise

    async def _connect(self) -> None:
        async with self.lock:
            process_alive = self.settings.browser_engine == "chromium" or (
                self.process and self.process.returncode is None
            )
            if self.browser and self.browser.is_connected() and process_alive:
                return
            if self.settings.browser_engine == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=True
                )
                return
            if self.process is None or self.process.returncode is not None:
                self.process = await asyncio.create_subprocess_exec(
                    self.settings.lightpanda_path,
                    "serve",
                    "--host",
                    self.settings.lightpanda_host,
                    "--port",
                    str(self.settings.lightpanda_port),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            deadline = monotonic() + self.settings.browser_start_timeout
            while monotonic() < deadline:
                if self.process.returncode is not None:
                    break
                try:
                    self.browser = (
                        await self.playwright.chromium.connect_over_cdp(
                            f"ws://127.0.0.1:{self.settings.lightpanda_port}",
                            timeout=1000,
                        )
                    )
                    return
                except Exception:
                    await asyncio.sleep(0.1)
            raise TicketError(
                "BROWSER_UNAVAILABLE", "Browser is not ready.", 503
            )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[None]:
        """Limit entire workflows, including the rendering fallback."""
        async with self.semaphore:
            yield

    @asynccontextmanager
    async def context(
        self, *, rendering: bool = False
    ) -> AsyncIterator[BrowserContext]:
        """Create a fresh context and close it on every exit path."""
        try:
            await self._connect()
            browser = self.browser
            if rendering and self.settings.browser_engine == "lightpanda":
                browser = await self._rendering_browser()
            context = await browser.new_context(accept_downloads=False)
        except TicketError:
            raise
        except Exception:
            raise TicketError(
                "BROWSER_UNAVAILABLE", "Browser is not available.", 503
            ) from None
        context.set_default_timeout(self.settings.page_timeout_ms)
        try:
            yield context
        finally:
            await context.close()

    async def _rendering_browser(self) -> Browser:
        async with self.lock:
            if not self.renderer or not self.renderer.is_connected():
                self.renderer = await self.playwright.chromium.launch(
                    headless=True
                )
            return self.renderer

    async def healthy(self) -> bool:
        """Probe CDP with an actual browser command."""
        try:
            async with asyncio.timeout(3):
                await self._connect()
                session = await self.browser.new_browser_cdp_session()
                try:
                    await session.send("Browser.getVersion")
                finally:
                    await session.detach()
                if self.settings.browser_engine == "lightpanda":
                    await self._rendering_browser()
                return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close connections and terminate the managed Lightpanda process."""
        for browser in (self.renderer, self.browser):
            if browser:
                with suppress(Exception):
                    await browser.close()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.playwright:
            await self.playwright.stop()
        self.playwright = None
        self.browser = None
        self.renderer = None
        self.process = None
