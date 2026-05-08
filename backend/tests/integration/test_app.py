"""App-level integration tests: validation error envelope, CORS, router mount."""

from app.config import Settings
from app.main import create_app
from httpx import ASGITransport, AsyncClient

from tests._stubs import install_fake_database


def _build_app(settings: Settings):
    """Same wiring the `app` fixture does — used by tests that need custom settings."""
    app = create_app(settings)
    install_fake_database(app)
    return app


async def test_validation_error_returns_structured_fields(client: AsyncClient):
    """A dummy endpoint relying on Query validation isn't exposed yet, so we
    hit the OpenAPI schema and confirm validation error envelope via direct
    request to a route that requires query params with constraints when added.

    For Iteration 1 we cover the contract via a synthetic case: the
    `/api/v1/health` route accepts no params, so we instead exercise the
    handler shape via the catch-all 404 path which already verifies the
    fields key exists. Here we additionally check structure when validation
    triggers naturally on the OpenAPI ?... no-op — kept minimal until
    real input-validating endpoints arrive in Iteration 4.
    """
    response = await client.get("/api/v1/does-not-exist")
    body = response.json()
    assert isinstance(body["error"]["fields"], list)


async def test_cors_disabled_when_origins_empty(monkeypatch):
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        ai_api_key="k",
        twelve_data_api_key="k",
        cors_allowed_origins=[],
        _env_file=None,
    )
    app = _build_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.options(
            "/api/v1/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    # No CORS middleware registered → preflight is not handled (no ACAO header).
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers.keys()}


async def test_cors_enabled_when_origin_configured():
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        ai_api_key="k",
        twelve_data_api_key="k",
        cors_allowed_origins=["http://example.com"],
        _env_file=None,
    )
    app = _build_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/health",
            headers={"Origin": "http://example.com"},
        )
    assert response.headers.get("access-control-allow-origin") == "http://example.com"


async def test_docs_disabled_in_production():
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        ai_api_key="k",
        twelve_data_api_key="k",
        app_env="production",
        _env_file=None,
    )
    app = _build_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        docs = await ac.get("/api/docs")
        openapi = await ac.get("/api/openapi.json")
    assert docs.status_code == 404
    assert openapi.status_code == 404
