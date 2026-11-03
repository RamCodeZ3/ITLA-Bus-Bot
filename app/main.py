"""FastAPI entry point and managed browser lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.application.event_bus import EventBus, ReplyRegistry
from app.application.handlers import WorkflowHandlers
from app.application.ports import TicketGateway
from app.config import Settings
from app.infrastructure.browser.provider import BrowserProvider
from app.infrastructure.scraper.gateway import ItlaGateway
from app.logging_config import correlation_id, setup_logging
from app.presentation.errors import install_error_handlers
from app.presentation.router import router


def create_app(
    settings: Settings | None = None,
    gateway: TicketGateway | None = None,
    provider: BrowserProvider | None = None,
) -> FastAPI:
    """Build the API; test gateways skip real browser startup."""
    config = settings or Settings()
    setup_logging(config.log_level)
    browser = provider or BrowserProvider(config)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Manage browser readiness and cancellation on shutdown."""
        try:
            if gateway is None:
                await browser.start()
            bus = EventBus()
            replies = ReplyRegistry(bus)
            WorkflowHandlers(bus, replies, gateway or ItlaGateway(browser))
            application.state.replies = replies
            yield
        finally:
            if hasattr(application.state, "replies"):
                await application.state.replies.close()
            if gateway is None:
                await browser.close()

    app = FastAPI(title="ITLA Tickets API", version="2.0.0", lifespan=lifespan)
    app.state.settings = config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
        expose_headers=["X-Correlation-ID"],
    )

    @app.middleware("http")
    async def correlate(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Attach a fresh request identifier and prevent response caching."""
        request.state.correlation_id = str(uuid4())
        token = correlation_id.set(request.state.correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = request.state.correlation_id
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            correlation_id.reset(token)

    @app.get("/health")
    async def health() -> JSONResponse:
        """Return actual browser readiness without revealing configuration."""
        ready = await browser.healthy()
        return JSONResponse(
            {
                "status": "ok" if ready else "unavailable",
                "browser_ready": ready,
            },
            status_code=200 if ready else 503,
        )

    install_error_handlers(app)
    app.include_router(router)
    return app
