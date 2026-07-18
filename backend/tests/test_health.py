from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "up"
    assert data["cache"] == "up"


def test_health_db_down():
    import backend.db
    from sqlalchemy.ext.asyncio import create_async_engine

    bad_engine = create_async_engine(
        "postgresql+asyncpg://bad:bad@localhost:1/nonexistent"
    )

    with patch.object(backend.db, "engine", bad_engine):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "down"


def test_health_cache_down():
    from backend.utils.cache import cache
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis connection refused")
    cache.redis_client = mock_redis

    try:
        response = client.get("/health")
    finally:
        cache.redis_client = None

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["cache"] == "down"


def test_health_both_down():
    import backend.db
    from backend.utils.cache import cache
    from sqlalchemy.ext.asyncio import create_async_engine

    bad_engine = create_async_engine(
        "postgresql+asyncpg://bad:bad@localhost:1/nonexistent"
    )

    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis down")
    cache.redis_client = mock_redis

    try:
        with patch.object(backend.db, "engine", bad_engine):
            response = client.get("/health")
    finally:
        cache.redis_client = None

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "down"
    assert data["cache"] == "down"
