from __future__ import annotations

import collections.abc
import inspect
import pathlib
import typing
import unittest.mock

import pytest
from httpx import ASGITransport, AsyncClient

from moviedb_manager.app import app
from moviedb_manager.config.settings import settings as app_settings


@pytest.mark.asyncio
async def test_full_movie_processing_pipeline(
    media_root: pathlib.Path,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
) -> None:
    """
    Integration test: API -> Background Task -> Pipeline -> FileOps -> DB.
    Mocks external APIs and qBittorrent but runs the full logic.
    """
    # 1. Setup host environment (redirecting settings to tmp_path)
    app_settings.directories.local = str(media_root)
    app_settings.directories.remote = str(media_root)

    # 2. Mock external dependencies
    background_tasks_list: list[
        tuple[typing.Any, tuple[typing.Any, ...], dict[str, typing.Any]]
    ] = []

    def mock_add_task(
        func: collections.abc.Callable[..., typing.Any],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        background_tasks_list.append((func, args, kwargs))

    # Ensure mock_db methods are correctly mocked (add is sync, others async)
    mock_db.add = unittest.mock.MagicMock()
    mock_db.commit = unittest.mock.AsyncMock()
    mock_db.refresh = unittest.mock.AsyncMock()

    with (
        unittest.mock.patch(
            "moviedb_manager.app.TmdbMovieAdapter"
        ) as mock_movie_adapter_cls,
        unittest.mock.patch("moviedb_manager.app.TvDbAdapter"),
        unittest.mock.patch(
            "moviedb_manager.app.qbittorrentapi.Client"
        ) as mock_qbt_cls,
        unittest.mock.patch(
            "moviedb_manager.app.redis.from_url"
        ) as mock_redis_from_url,
        unittest.mock.patch(
            "moviedb_manager.app.AsyncSessionLocal"
        ) as mock_session_factory,
        unittest.mock.patch(
            "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
        ),
        # Collect background tasks
        unittest.mock.patch(
            "fastapi.BackgroundTasks.add_task", side_effect=mock_add_task
        ),
    ):
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        # Setup Mocks
        mock_movie_db = mock_movie_adapter_cls.return_value
        mock_movie_db.search.return_value = [
            unittest.mock.MagicMock(
                original_title="Interstellar", release_date="2014-11-07"
            )
        ]

        mock_qbt = mock_qbt_cls.return_value
        mock_qbt.torrents_add.return_value = "Ok."
        mock_qbt.torrents_info.side_effect = [
            [
                {
                    "hash": "h1",
                    "name": "Interstellar.2014.1080p",
                    "magnet_uri": "magnet:?xt=urn:btih:movie123",
                }
            ],
            [
                {
                    "state": "completed",
                    "hash": "h1",
                    "progress": 1.0,
                    "eta": 0,
                    "name": "Interstellar.2014.1080p",
                }
            ],
        ]
        mock_qbt.torrents_files.return_value = [
            {"name": "Interstellar.2014.1080p/movie.mkv"}
        ]

        mock_redis_client = unittest.mock.AsyncMock()
        mock_redis_from_url.return_value = mock_redis_client

        # Create the physical file in the mock download dir
        download_path = media_root / "downloads" / "Interstellar.2014.1080p"
        download_path.mkdir(parents=True, exist_ok=True)
        (download_path / "movie.mkv").touch()

        # 3. Trigger via API
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/torrents",
                json={
                    "magnet_uri": "magnet:?xt=urn:btih:movie123",
                    "media_type": "movie",
                },
            )

        assert response.status_code == 200

        # 4. Await background tasks (INSIDE the patch context)
        for func, args, kwargs in background_tasks_list:
            if inspect.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)

        # 5. Verification
        # Verify file movement
        movie_path = media_root / "movies" / "Interstellar (2014).mkv"
        assert movie_path.exists(), f"Expected {movie_path} to exist"

        # Verify DB updates
        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_full_tv_processing_pipeline(
    media_root: pathlib.Path,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
) -> None:
    """
    Integration test: TV episode flow.
    """
    app_settings.directories.local = str(media_root)
    app_settings.directories.remote = str(media_root)

    background_tasks_list: list[
        tuple[typing.Any, tuple[typing.Any, ...], dict[str, typing.Any]]
    ] = []

    def mock_add_task(
        func: collections.abc.Callable[..., typing.Any],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        background_tasks_list.append((func, args, kwargs))

    mock_db.add = unittest.mock.MagicMock()
    mock_db.commit = unittest.mock.AsyncMock()
    mock_db.refresh = unittest.mock.AsyncMock()

    with (
        unittest.mock.patch("moviedb_manager.app.TmdbMovieAdapter") as _,
        unittest.mock.patch("moviedb_manager.app.TvDbAdapter") as mock_tv_adapter_cls,
        unittest.mock.patch(
            "moviedb_manager.app.qbittorrentapi.Client"
        ) as mock_qbt_cls,
        unittest.mock.patch(
            "moviedb_manager.app.redis.from_url"
        ) as mock_redis_from_url,
        unittest.mock.patch(
            "moviedb_manager.app.AsyncSessionLocal"
        ) as mock_session_factory,
        unittest.mock.patch(
            "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
        ),
        unittest.mock.patch(
            "fastapi.BackgroundTasks.add_task", side_effect=mock_add_task
        ),
    ):
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        mock_tv_db = mock_tv_adapter_cls.return_value
        mock_tv_db.search_series.return_value = [
            {"id": "series-1", "tvdb_id": "1", "name": "The Mandalorian"}
        ]
        mock_tv_db.get_series_name.return_value = "The Mandalorian"
        mock_tv_db.get_episode_name.return_value = "The Jedi"

        mock_qbt = mock_qbt_cls.return_value
        mock_qbt.torrents_add.return_value = "Ok."
        mock_qbt.torrents_info.side_effect = [
            [
                {
                    "hash": "h2",
                    "name": "Mandalorian.S02E05",
                    "magnet_uri": "magnet:?xt=urn:btih:tv123",
                }
            ],
            [
                {
                    "state": "completed",
                    "hash": "h2",
                    "progress": 1.0,
                    "eta": 0,
                    "name": "Mandalorian.S02E05",
                }
            ],
        ]
        mock_qbt.torrents_files.return_value = [
            {"name": "Mandalorian.S02E05/The.Mandalorian.S02E05.mp4"}
        ]

        mock_redis_client = unittest.mock.AsyncMock()
        mock_redis_from_url.return_value = mock_redis_client

        download_path = media_root / "downloads" / "Mandalorian.S02E05"
        download_path.mkdir(parents=True, exist_ok=True)
        (download_path / "The.Mandalorian.S02E05.mp4").touch()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/torrents",
                json={"magnet_uri": "magnet:?xt=urn:btih:tv123", "media_type": "tv"},
            )

        assert response.status_code == 200

        # Await background tasks (INSIDE patch context)
        for func, args, kwargs in background_tasks_list:
            if inspect.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)

        # Verify file movement
        tv_path = (
            media_root
            / "tv"
            / "The Mandalorian"
            / "Season 2"
            / "The Mandalorian - S02E05 - The Jedi.mp4"
        )
        assert tv_path.exists(), f"Expected {tv_path} to exist"
        assert mock_db.commit.called
