from datetime import datetime, timezone
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def get_current_iso_timestamp() -> str:
    """Returns ISO-8601 timestamp with explicit UTC or local timezone offset."""
    return datetime.now(timezone.utc).isoformat()


class BaseAPIException(Exception):
    """Base exception for all application API errors."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        timestamp: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.timestamp = timestamp or get_current_iso_timestamp()
        super().__init__(message)


class ResourceNotFoundError(BaseAPIException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with ID '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationError(BaseAPIException):
    def __init__(self, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class DatabaseConnectionError(BaseAPIException):
    def __init__(self, message: str = "Unable to connect to database"):
        super().__init__(
            code="DATABASE_CONNECTION_ERROR",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


async def custom_api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Formats BaseAPIException into the standard API error contract."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "timestamp": exc.timestamp,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats Pydantic RequestValidationError into the standard API error contract."""
    first_error = exc.errors()[0] if exc.errors() else {"msg": "Validation failed", "loc": []}
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    msg = first_error.get("msg", "Invalid value")
    formatted_message = f"Field '{field}': {msg}" if field else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": formatted_message,
                "timestamp": get_current_iso_timestamp(),
            }
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Formats standard HTTPExceptions into the standard API error contract."""
    code_map = {
        404: "RESOURCE_NOT_FOUND",
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "ERROR")
    message = str(exc.detail) if hasattr(exc, "detail") else "An error occurred"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "timestamp": get_current_iso_timestamp(),
            }
        },
    )


async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Formats database exceptions into the standard HTTP 503 API error contract."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "DATABASE_CONNECTION_ERROR",
                "message": "Database service is temporarily unavailable.",
                "timestamp": get_current_iso_timestamp(),
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Formats generic unhandled server exceptions safely without leaking internal secrets."""
    # If the unhandled exception was caused by a database dropout or network failure, map to 503
    exc_name = type(exc).__name__
    if "Database" in exc_name or "Connection" in exc_name or "OperationalError" in exc_name or "InterfaceError" in exc_name:
        return await database_exception_handler(request, exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "timestamp": get_current_iso_timestamp(),
            }
        },
    )
