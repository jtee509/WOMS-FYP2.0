"""
WOMS Common Schemas

Shared response models for pagination, errors, and standard envelopes.
Used across all domain routers for consistent frontend (React + MUI) integration.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard wrapper for paginated list responses."""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Single error entry."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all endpoints."""
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Generic success
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Simple message response for operations without data payload."""
    message: str
    status: str = "ok"
