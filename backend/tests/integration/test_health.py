from app import __version__
from httpx import ASGITransport, AsyncClient

from tests._stubs import install_fake_database


async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_health_status_is_ok(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    assert data["status"] == "ok"


async def test_health_contains_required_fields(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    for key in ("status", "version", "environment", "timestamp", "python_version", "components"):
        assert key in data


async def test_health_reports_package_version(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    assert data["version"] == __version__


async def test_health_components_have_status(client: AsyncClient):
    components = (await client.get("/api/v1/health")).json()["components"]
    assert "database" in components
    assert "scheduler" in components
    for component in components.values():
        assert "status" in component


async def test_health_reports_database_ok_when_reachable(client: AsyncClient):
    """The default fake Database returns healthy=True, so the probe must
    surface that as an `ok` component status."""
    data = (await client.get("/api/v1/health")).json()
    assert data["components"]["database"]["status"] == "ok"


async def test_health_reports_database_down_when_probe_fails(app):
    """A failing healthcheck must downgrade the component to `down` and
    propagate that to the overall status."""
    install_fake_database(app, healthy=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        data = (await ac.get("/api/v1/health")).json()
    assert data["components"]["database"]["status"] == "down"
    assert data["components"]["database"]["detail"] == "Database unreachable"
    assert data["status"] == "down"


async def test_health_environment_is_development(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    assert data["environment"] == "development"


async def test_unknown_route_returns_404_error_shape(client: AsyncClient):
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "fields" in body["error"]


async def test_docs_available_in_development(client: AsyncClient):
    response = await client.get("/api/docs")
    assert response.status_code == 200


async def test_openapi_schema_available_in_development(client: AsyncClient):
    data = (await client.get("/api/openapi.json")).json()
    assert data["info"]["title"] == "TradeSignal AI"
    assert data["info"]["version"] == __version__
    assert "/api/v1/health" in data["paths"]
