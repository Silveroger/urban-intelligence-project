from typing import Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of the error")
    timestamp: str = Field(..., description="ISO-8601 timestamp of when the error occurred")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200, description="Maximum items to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
