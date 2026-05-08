from app.schemas.common import (
    APIResponse,
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.schemas.health import ComponentStatus, HealthResponse

# ── APIResponse / ErrorResponse ────────────────────────────────────────────


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
    assert response.error.fields == []


def test_error_response_serialises_to_json():
    response = ErrorResponse(error=ErrorDetail(code="INTERNAL_ERROR", message="Boom"))
    dumped = response.model_dump(mode="json")
    assert dumped["success"] is False
    assert dumped["error"]["code"] == "INTERNAL_ERROR"
    assert dumped["error"]["fields"] == []


def test_error_response_can_carry_field_errors():
    detail = ErrorDetail(
        code="VALIDATION_ERROR",
        message="1 validation error(s)",
        fields=[{"loc": ["body", "page"], "msg": "must be >= 1", "type": "greater_than_equal"}],
    )
    dumped = ErrorResponse(error=detail).model_dump(mode="json")
    assert dumped["error"]["fields"][0]["loc"] == ["body", "page"]


# ── Pagination ─────────────────────────────────────────────────────────────


def test_pagination_meta_computes_pages():
    meta = PaginationMeta(total=95, page=2, per_page=20)
    assert meta.pages == 5


def test_pagination_meta_pages_zero_when_empty():
    meta = PaginationMeta(total=0, page=1, per_page=20)
    assert meta.pages == 0


def test_pagination_meta_pages_round_up():
    meta = PaginationMeta(total=21, page=1, per_page=20)
    assert meta.pages == 2


def test_pagination_meta_pages_appears_in_dump():
    dumped = PaginationMeta(total=40, page=1, per_page=20).model_dump(mode="json")
    assert dumped["pages"] == 2


def test_paginated_response_structure():
    meta = PaginationMeta(total=2, page=1, per_page=20)
    response = PaginatedResponse[str](data=["a", "b"], pagination=meta)
    assert response.success is True
    assert response.data == ["a", "b"]
    assert response.pagination.pages == 1


def test_paginated_response_serialises_cleanly():
    meta = PaginationMeta(total=1, page=1, per_page=20)
    response = PaginatedResponse[int](data=[42], pagination=meta)
    dumped = response.model_dump(mode="json")
    assert dumped["success"] is True
    assert dumped["data"] == [42]
    assert dumped["pagination"]["total"] == 1
    assert dumped["pagination"]["pages"] == 1


# ── Health schemas ─────────────────────────────────────────────────────────


def test_component_status_accepts_known_states():
    assert ComponentStatus(status="ok").status == "ok"
    assert ComponentStatus(status="not_configured").status == "not_configured"


def test_health_response_round_trips():
    from datetime import UTC, datetime

    response = HealthResponse(
        status="ok",
        version="0.1.0",
        environment="development",
        timestamp=datetime.now(UTC),
        python_version="3.12.0",
        components={"database": ComponentStatus(status="not_configured")},
    )
    dumped = response.model_dump(mode="json")
    assert dumped["status"] == "ok"
    assert dumped["components"]["database"]["status"] == "not_configured"
