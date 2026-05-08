from app.dependencies import Pagination


def test_pagination_offset_and_limit():
    p = Pagination(page=3, per_page=20)
    assert p.offset == 40
    assert p.limit == 20


def test_pagination_first_page_has_zero_offset():
    p = Pagination(page=1, per_page=50)
    assert p.offset == 0
    assert p.limit == 50


def test_pagination_is_immutable():
    """Frozen dataclass — accidental mutation in handlers fails fast."""
    import dataclasses

    p = Pagination(page=1, per_page=20)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        p.page = 5  # type: ignore[misc]
