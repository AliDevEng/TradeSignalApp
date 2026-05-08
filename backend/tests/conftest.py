"""Shared pytest fixtures.

The HTTP client is wired via ASGITransport so tests do not need a running
uvicorn process. Each test session gets a freshly built FastAPI app via
`create_app()` so test isolation is preserved when settings change.
"""

from collections.abc import AsyncIterator

import pytest
from app.config import get_settings
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache between tests so env patches take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """Async HTTP client wired to the ASGI app — no real server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
