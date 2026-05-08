from fastapi import Query
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse[T](BaseModel):
    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse[T](BaseModel):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta


class PaginationParams:
    """Reusable FastAPI dependency for paginated list endpoints."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
        per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page
