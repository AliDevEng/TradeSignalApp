from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_health_status_is_ok(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    assert data["status"] == "ok"


async def test_health_contains_required_fields(client: AsyncClient):
    data = (await client.get("/api/v1/health")).json()
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "python_version" in data
    assert "components" in data


async def test_health_components_have_status(client: AsyncClient):
    components = (await client.get("/api/v1/health")).json()["components"]
    assert "database" in components
    assert "scheduler" in components
    for component in components.values():
        assert "status" in component


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


async def test_docs_available_in_development(client: AsyncClient):
    response = await client.get("/api/docs")
    assert response.status_code == 200


async def test_openapi_schema_available_in_development(client: AsyncClient):
    data = (await client.get("/api/openapi.json")).json()
    assert data["info"]["title"] == "TradeSignal AI"
    assert "paths" in data
    assert "/api/v1/health" in data["paths"]
