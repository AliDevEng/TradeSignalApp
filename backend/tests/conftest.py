"""Shared pytest fixtures.

The HTTP client is wired via ASGITransport so tests do not need a running
uvicorn process. Each test session gets a freshly built FastAPI app via
`create_app()` so test isolation is preserved when settings change.

Every test app gets its real `Database` swapped for a `FakeDatabase` —
`create_app()` constructs the engine eagerly (sync) but never opens a
connection until something runs SQL, and we don't want tests to ever
reach a live Postgres. Tests that want to simulate DB failure should use
`install_fake_database(app, healthy=False)` directly.
"""

from collections.abc import AsyncIterator

import pytest
from app.config import get_settings
from app.main import create_app
from httpx import ASGITransport, AsyncClient

from tests._stubs import install_fake_database


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache between tests so env patches take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    application = create_app()
    install_fake_database(application)
    return application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """Async HTTP client wired to the ASGI app — no real server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
