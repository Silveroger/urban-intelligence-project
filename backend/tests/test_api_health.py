import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_database_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health/database")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "status" in data["database"]
