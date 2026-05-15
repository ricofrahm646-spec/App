from __future__ import annotations

import time
import traceback
from typing import Any, Callable

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("jarvis.middleware")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches all unhandled exceptions and returns a uniform JSON envelope."""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            elapsed = time.perf_counter() - start
            response.headers["X-Process-Time"] = f"{elapsed:.4f}"
            return response
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                traceback=traceback.format_exc(),
                elapsed=f"{elapsed:.4f}",
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "An unexpected error occurred.",
                    "data": None,
                },
            )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg", "")})
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Request validation failed.",
            "data": {"errors": errors},
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "unhandled_exception_handler",
        path=request.url.path,
        error=str(exc),
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error.",
            "data": None,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]
