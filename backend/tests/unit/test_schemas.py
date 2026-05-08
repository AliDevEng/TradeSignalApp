from app.schemas.common import (
    APIResponse,
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
)


def test_api_response_wraps_payload():
    response = APIResponse[dict](data={"key": "value"})
    assert response.success is True
    assert response.data == {"key": "value"}


def test_api_response_serialises_to_json():
    response = APIResponse[str](data="hello")
    dumped = response.model_dump(mode="json")
    assert dumped == {"success": True, "data": "hello"}


def test_error_response_structure():
    response = ErrorResponse(error=ErrorDetail(code="NOT_FOUND", message="Resource not found"))
    assert response.success is False
    assert response.error.code == "NOT_FOUND"
    assert response.error.message == "Resource not found"


def test_error_response_serialises_to_json():
    response = ErrorResponse(error=ErrorDetail(code="INTERNAL_ERROR", message="Boom"))
    dumped = response.model_dump(mode="json")
    assert dumped["success"] is False
    assert dumped["error"]["code"] == "INTERNAL_ERROR"


def test_paginated_response_computes_pages():
    meta = PaginationMeta(total=95, page=2, per_page=20, pages=5)
    response = PaginatedResponse[str](data=["a", "b"], pagination=meta)
    assert response.success is True
    assert len(response.data) == 2
    assert response.pagination.pages == 5


def test_paginated_response_serialises_cleanly():
    meta = PaginationMeta(total=1, page=1, per_page=20, pages=1)
    response = PaginatedResponse[int](data=[42], pagination=meta)
    dumped = response.model_dump(mode="json")
    assert dumped["success"] is True
    assert dumped["data"] == [42]
    assert dumped["pagination"]["total"] == 1
