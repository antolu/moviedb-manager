from __future__ import annotations

import asyncio
import collections.abc
import unittest.mock

import pytest
from httpx import ASGITransport, AsyncClient

import moviedb_manager
from moviedb_manager.app import (
    app,
    configure_frontend,
    event_generator,
    get_db,
    lifespan,
    main,
    run_pipeline_task,
)


@pytest.fixture
def override_db(
    mock_db: unittest.mock.AsyncMock,
) -> collections.abc.Generator[unittest.mock.AsyncMock]:
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_torrents_endpoint(
    override_db: unittest.mock.AsyncMock, mock_redis: unittest.mock.AsyncMock
) -> None:
    app.state.redis = mock_redis
    mock_torrent = unittest.mock.MagicMock()
    mock_execute_result = unittest.mock.MagicMock()
    override_db.execute.return_value = mock_execute_result
    mock_execute_result.scalars.return_value.all.return_value = [mock_torrent]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/torrents")

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_history_endpoint(
    override_db: unittest.mock.AsyncMock, mock_redis: unittest.mock.AsyncMock
) -> None:
    app.state.redis = mock_redis
    mock_file = unittest.mock.MagicMock()
    mock_execute_result = unittest.mock.MagicMock()
    override_db.execute.return_value = mock_execute_result
    mock_execute_result.scalars.return_value.all.return_value = [mock_file]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/history")

    assert response.status_code == 200
    assert len(response.json()) == 1


@unittest.mock.patch(
    "moviedb_manager.app.asyncio.sleep", side_effect=asyncio.CancelledError
)
@pytest.mark.asyncio
async def test_stream_torrents_endpoint(
    mock_sleep: unittest.mock.AsyncMock, mock_redis: unittest.mock.AsyncMock
) -> None:
    # Set up mock redis in app state
    app.state.redis = mock_redis
    mock_redis.keys.return_value = ["torrent:1"]
    mock_redis.hgetall.return_value = {"name": "Test", "progress": "0.5"}

    try:
        async with (
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
            ac.stream("GET", "/api/torrents/stream") as response,
        ):
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    assert "Test" in line
                    break
    except asyncio.CancelledError:
        pass


@unittest.mock.patch(
    "moviedb_manager.app.asyncio.sleep", side_effect=asyncio.CancelledError
)
@pytest.mark.asyncio
async def test_stream_torrents_sse_direct(
    mock_sleep: unittest.mock.AsyncMock, mock_redis: unittest.mock.AsyncMock
) -> None:

    mock_redis.keys.return_value = ["torrent:1", "torrent:2"]
    mock_redis.hgetall.side_effect = [
        {"name": "Test1", "progress": "0.5"},
        {"name": "Test2", "progress": "0.8"},
    ]

    mock_request = unittest.mock.MagicMock()
    mock_request.is_disconnected = unittest.mock.AsyncMock(return_value=False)

    gen = event_generator(mock_request, mock_redis)
    async for val in gen:
        assert "data" in val
        assert len(val["data"]) >= 1


@pytest.mark.asyncio
async def test_stream_torrents_sse_disconnect(
    mock_redis: unittest.mock.AsyncMock,
) -> None:

    mock_request = unittest.mock.MagicMock()
    mock_request.is_disconnected = unittest.mock.AsyncMock(return_value=True)

    gen = event_generator(mock_request, mock_redis)
    async for _ in gen:
        pytest.fail("Should have disconnected immediately")


@pytest.mark.asyncio
async def test_run_pipeline_task_direct() -> None:

    mock_session = unittest.mock.AsyncMock()
    mock_context_manager = unittest.mock.AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_session
    mock_context_manager.__aexit__ = unittest.mock.AsyncMock()

    mock_redis_client = unittest.mock.AsyncMock()

    with (
        unittest.mock.patch(
            "moviedb_manager.app.process_torrent_pipeline"
        ) as mock_pipeline,
        unittest.mock.patch(
            "moviedb_manager.app.redis.from_url", return_value=mock_redis_client
        ),
        unittest.mock.patch("moviedb_manager.app.qbittorrentapi.Client"),
        unittest.mock.patch("moviedb_manager.app.TmdbMovieAdapter"),
        unittest.mock.patch("moviedb_manager.app.TvDbAdapter"),
        unittest.mock.patch(
            "moviedb_manager.app.AsyncSessionLocal", return_value=mock_context_manager
        ),
    ):
        await run_pipeline_task("magnet:...", "movie")
        assert mock_pipeline.called
        assert mock_redis_client.close.called


@pytest.mark.asyncio
async def test_lifespan_qbt_failure() -> None:

    app_mock = unittest.mock.MagicMock()
    app_mock.state = unittest.mock.MagicMock()
    app_mock.state.redis.close = unittest.mock.AsyncMock()

    with (
        unittest.mock.patch(
            "moviedb_manager.app.qbittorrentapi.Client"
        ) as mock_qbt_cls,
        unittest.mock.patch(
            "moviedb_manager.app.redis.from_url"
        ) as mock_redis_from_url,
        unittest.mock.patch("moviedb_manager.app.TmdbMovieAdapter"),
        unittest.mock.patch("moviedb_manager.app.TvDbAdapter"),
    ):
        mock_redis_from_url.return_value = app_mock.state.redis
        mock_qbt = mock_qbt_cls.return_value
        mock_qbt.app_version.side_effect = Exception("Connection Refused")

        async with lifespan(app_mock):
            pass

        assert mock_qbt.app_version.called
        assert app_mock.state.redis.close.called


def test_configure_frontend_logic(tmp_path: str) -> None:
    app_mock = unittest.mock.MagicMock()

    with (
        unittest.mock.patch("os.path.exists", side_effect=lambda p: "static" in p),
        unittest.mock.patch("moviedb_manager.app.StaticFiles") as mock_static,
    ):
        configure_frontend(app_mock)
        assert app_mock.mount.called
        assert mock_static.called

    app_mock.reset_mock()
    with (
        unittest.mock.patch("os.path.exists", side_effect=lambda p: "dist" in p),
        unittest.mock.patch("moviedb_manager.app.StaticFiles") as mock_static,
    ):
        configure_frontend(app_mock)
        assert app_mock.mount.called
        assert mock_static.called


def test_main_call() -> None:

    with unittest.mock.patch("uvicorn.run") as mock_run:
        main()
        assert mock_run.called


def test_version_import() -> None:

    assert moviedb_manager.__version__ is not None
