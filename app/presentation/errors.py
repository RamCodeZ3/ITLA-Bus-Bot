"""Central HTTP error mapping with no credential-bearing input echoes."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.domain.exceptions import TicketError


def error_response(
    request: Request, code: str, message: str, status: int
) -> JSONResponse:
    """Build the uniform public error envelope."""
    return JSONResponse(
        status_code=status,
        headers={
            "X-Correlation-ID": request.state.correlation_id,
            "Cache-Control": "no-store",
        },
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": request.state.correlation_id,
            }
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register safe mappings for domain, validation and HTTP failures."""

    @app.exception_handler(TicketError)
    async def domain_error(request: Request, exc: TicketError) -> JSONResponse:
        """Map safe domain errors to their explicit HTTP status."""
        return error_response(request, exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Report validation failures without echoing request inputs."""
        # Do not return Pydantic's input field: it can contain passwords.
        messages = []
        for item in exc.errors():
            path = ".".join(str(part) for part in item["loc"])
            message = item["msg"]
            messages.append(f"{path}: {message}")
        return error_response(
            request, "VALIDATION_ERROR", "; ".join(messages), 422
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        """Normalize framework HTTP errors."""
        return error_response(
            request, "HTTP_ERROR", "HTTP request rejected.", exc.status_code
        )

    @app.exception_handler(Exception)
    async def unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Hide unexpected exception details from public responses."""
        return error_response(
            request, "INTERNAL_ERROR", "Unexpected API failure.", 500
        )
