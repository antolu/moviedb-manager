from __future__ import annotations

import unittest.mock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from moviedb_manager.app import app
from moviedb_manager.app import lifespan as app_lifespan

# For simple tests that don't need lifespan/async
client = TestClient(app)


@pytest.mark.asyncio
async def test_status_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)


@pytest.mark.asyncio
async def test_add_torrent_success() -> None:
    # Mock the fastapi BackgroundTasks.add_task method
    with unittest.mock.patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/torrents",
                json={"magnet_uri": "magnet:?xt=urn:btih:123", "media_type": "movie"},
            )
        assert response.status_code == 200
        assert "message" in response.json()
        mock_add_task.assert_called_once()


@pytest.mark.asyncio
async def test_add_torrent_invalid_magnet() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/torrents",
            json={"magnet_uri": "invalid", "media_type": "movie"},
        )
    assert response.status_code == 400
    assert "Invalid magnet URI" in response.json()["detail"]


@pytest.mark.asyncio
async def test_lifespan_initialization() -> None:
    # Test that lifespan sets up the state
    app_mock = unittest.mock.MagicMock()
    app_mock.state = unittest.mock.MagicMock()

    with (
        unittest.mock.patch("moviedb_manager.app.qbittorrentapi.Client"),
        unittest.mock.patch("moviedb_manager.app.TmdbMovieAdapter"),
        unittest.mock.patch("moviedb_manager.app.TvDbAdapter"),
        unittest.mock.patch(
            "moviedb_manager.app.redis.from_url"
        ) as mock_redis_from_url,
    ):
        mock_redis = unittest.mock.AsyncMock()
        mock_redis_from_url.return_value = mock_redis

        async with app_lifespan(app_mock):
            assert hasattr(app_mock.state, "movie_db")
            assert hasattr(app_mock.state, "tv_db")
            assert hasattr(app_mock.state, "qbt_client")
            assert hasattr(app_mock.state, "redis")

        mock_redis.close.assert_awaited_once()
