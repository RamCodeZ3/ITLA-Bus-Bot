"""JSON logging with correlation identifiers and no local files."""

import json
import logging
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    """Emit a bounded set of safe structured log fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize application messages without exception-local variables."""
        return json.dumps(
            {
                "level": record.levelname,
                "logger": record.name,
                "correlation_id": correlation_id.get(),
                "message": record.getMessage(),
            }
        )


def setup_logging(level: str) -> None:
    """Configure console-only application logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.error"):
        server_logger = logging.getLogger(name)
        server_logger.handlers.clear()
        server_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
