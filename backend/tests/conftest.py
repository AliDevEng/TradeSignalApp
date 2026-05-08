import pytest
from app.config import get_settings
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache between tests so env patches take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    """Async HTTP client wired to the ASGI app — no real server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
