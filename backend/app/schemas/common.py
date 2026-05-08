"""Transport-agnostic response envelopes shared across all v1 endpoints.

This module must NOT import FastAPI — schemas describe the wire format and
should be reusable from non-HTTP contexts (background jobs, internal RPC,
etc). Request-handling concerns (Query, Depends) live in `app.dependencies`.
"""

from __future__ import annotations

from math import ceil
from typing import Any

from pydantic import BaseModel, Field, computed_field


class ErrorDetail(BaseModel):
    code: str
    message: str
    # Field-level validation issues, if any. Stays empty for non-validation errors.
    fields: list[dict[str, Any]] = Field(default_factory=list)


class APIResponse[T](BaseModel):
    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return ceil(self.total / self.per_page)


class PaginatedResponse[T](BaseModel):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta
