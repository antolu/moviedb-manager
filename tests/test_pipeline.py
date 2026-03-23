from __future__ import annotations

import pathlib
import unittest.mock

import pytest

from moviedb_manager.config.settings import Settings
from moviedb_manager.models.media import TorrentInfo
from moviedb_manager.services.pipeline import process_torrent_pipeline
from tests.conftest import StubMovieDbClient, StubTvDbClient


@pytest.mark.asyncio
async def test_process_movie_pipeline(  # noqa: PLR0913,PLR0917
    media_root: pathlib.Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: Settings,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Setup stubs
    movie_db_stub.results = [
        unittest.mock.MagicMock(
            original_title="Interstellar", release_date="2014-11-07"
        )
    ]

    # Mock qBittorrent client
    qbt_mock = unittest.mock.MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.side_effect = [
        [
            {
                "hash": "h1",
                "name": "Interstellar.2014.1080p",
                "magnet_uri": "magnet:?xt=urn:btih:h1",
                "progress": 1.0,
                "state": "completed",
            }
        ],
        [
            {
                "state": "completed",
                "hash": "h1",
                "progress": 1.0,
                "name": "Interstellar.2014.1080p",
            }
        ],
    ]
    qbt_mock.torrents_files.return_value = [
        {"name": "Interstellar.2014.1080p/movie.mkv"}
    ]

    # Create the actual file
    download_path = media_root / "downloads" / "Interstellar.2014.1080p"
    download_path.mkdir(parents=True, exist_ok=True)
    mkv_file = download_path / "movie.mkv"
    mkv_file.touch()

    with unittest.mock.patch(
        "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
    ):
        await process_torrent_pipeline(
            magnet_uri="magnet:?xt=urn:btih:h1",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
            db=mock_db,
            redis_client=mock_redis,
        )

    # Verify
    movie_lib = media_root / "movies"
    assert (movie_lib / "Interstellar (2014).mkv").exists()
    assert not download_path.exists()
    assert mock_db.commit.call_count >= 2


@pytest.mark.asyncio
async def test_process_tv_pipeline(  # noqa: PLR0913,PLR0917
    media_root: pathlib.Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: Settings,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Setup stubs
    tv_db_stub.search_results = [
        {"id": "series-1", "tvdb_id": "1", "name": "The Mandalorian"}
    ]
    tv_db_stub.series_name = "The Mandalorian"
    tv_db_stub.episode_name = "The Jedi"

    # Mock qBittorrent client
    qbt_mock = unittest.mock.MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.side_effect = [
        [
            {
                "hash": "h2",
                "name": "Mandalorian.S02E05",
                "magnet_uri": "magnet:?xt=urn:btih:h2",
                "progress": 1.0,
                "state": "completed",
            }
        ],
        [
            {
                "state": "completed",
                "hash": "h2",
                "progress": 1.0,
                "name": "Mandalorian.S02E05",
            }
        ],
    ]
    qbt_mock.torrents_files.return_value = [
        {"name": "Mandalorian.S02E05/Mandalorian.S02E05.mp4"}
    ]

    # Create the actual file
    torrent_rel_dir = "Mandalorian.S02E05"
    mkv_rel_path = f"{torrent_rel_dir}/Mandalorian.S02E05.mp4"

    full_torrent_dir = media_root / "downloads" / torrent_rel_dir
    full_torrent_dir.mkdir(parents=True, exist_ok=True)
    mp4_file = media_root / "downloads" / mkv_rel_path
    mp4_file.touch()
    tv_db_stub.series_name = "The Mandalorian"
    tv_db_stub.episode_name = "The Jedi"

    monkeypatch.setattr(
        "moviedb_manager.services.torrent.asyncio.sleep", lambda *_: None
    )

    await process_torrent_pipeline(
        magnet_uri="magnet:?xt=urn:btih:h2",
        media_type="tv",
        qbt_client=qbt_mock,
        movie_db=movie_db_stub,
        tv_db=tv_db_stub,
        settings=settings,
        db=mock_db,
        redis_client=mock_redis,
    )

    # Verify
    tv_lib = media_root / "tv" / "The Mandalorian" / "Season 2"
    assert (tv_lib / "The Mandalorian - S02E05 - The Jedi.mp4").exists()
    assert not full_torrent_dir.exists()


@pytest.mark.asyncio
async def test_pipeline_no_media_files(  # noqa: PLR0913,PLR0917
    media_root: pathlib.Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: Settings,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
) -> None:
    qbt_mock = unittest.mock.MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.return_value = [
        {
            "hash": "h3",
            "name": "Empty",
            "magnet_uri": "magnet:?xt=urn:btih:h3",
            "state": "completed",
            "progress": 1.0,
        }
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Empty/nothing.txt"}]

    # Create empty dir
    download_path = media_root / "downloads" / "Empty"
    download_path.mkdir(parents=True, exist_ok=True)
    (download_path / "nothing.txt").touch()

    with (
        unittest.mock.patch(
            "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
        ),
        pytest.raises(RuntimeError, match="No media files found"),
    ):
        await process_torrent_pipeline(
            magnet_uri="magnet:?xt=urn:btih:h3",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
            db=mock_db,
            redis_client=mock_redis,
        )


@pytest.mark.asyncio
async def test_pipeline_multiple_files(  # noqa: PLR0913,PLR0917
    media_root: pathlib.Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: Settings,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie_db_stub.results = [
        unittest.mock.MagicMock(original_title="Kill Bill", release_date="2003-10-10")
    ]
    qbt_mock = unittest.mock.MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.return_value = [
        {
            "hash": "h4",
            "name": "Kill.Bill",
            "magnet_uri": "magnet:?xt=urn:btih:h4",
            "state": "completed",
            "progress": 1.0,
        }
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Kill.Bill/vol1.mkv"}]

    download_path = media_root / "downloads" / "Kill.Bill"
    download_path.mkdir(parents=True, exist_ok=True)
    (download_path / "vol1.mkv").touch()
    (download_path / "vol2.mkv").touch()

    monkeypatch.setattr(
        "moviedb_manager.services.torrent.asyncio.sleep", lambda *_: None
    )
    with unittest.mock.patch(
        "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
    ):
        await process_torrent_pipeline(
            magnet_uri="magnet:?xt=urn:btih:h4",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
            db=mock_db,
            redis_client=mock_redis,
        )

    movie_lib = media_root / "movies"
    assert (movie_lib / "Kill Bill (2003).mkv").exists()
    assert len(list(movie_lib.glob("*.mkv"))) >= 1


@pytest.mark.asyncio
async def test_pipeline_multi_file_tv_torrent(
    settings: Settings,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
) -> None:
    # Torrent has two TV episodes
    local_base = pathlib.Path(settings.directories.local)
    torrent_dir = local_base / settings.directories.download / "Show.Torrent"
    torrent_dir.mkdir(parents=True)
    (torrent_dir / "Show.S01E01.mkv").touch()
    (torrent_dir / "Show.S01E02.mkv").touch()

    # Mock qbt client
    mock_qbt = unittest.mock.MagicMock()
    mock_qbt.torrents_files.return_value = [
        {"name": "Show.Torrent/Show.S01E01.mkv"},
        {"name": "Show.Torrent/Show.S01E02.mkv"},
    ]

    # Stubs
    tv_db_stub.search_results = [{"id": "series-1", "tvdb_id": "1", "name": "Show"}]
    tv_db_stub.series_name = "Show"
    tv_db_stub.episode_name = "Pilot"

    with unittest.mock.patch(
        "moviedb_manager.services.pipeline.add_and_wait_for_completion"
    ) as mock_add:
        mock_add.return_value = TorrentInfo(
            hash="h1",
            name="Show.Torrent",
            data_root="Show.Torrent",
            magnet_uri="magnet:?xt=urn:btih:h1",
            files=["Show.Torrent/Show.S01E01.mkv", "Show.Torrent/Show.S01E02.mkv"],
        )
        await process_torrent_pipeline(
            qbt_client=mock_qbt,
            magnet_uri="magnet:?xt=urn:btih:h1",
            media_type="tv",
            settings=settings,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            db=mock_db,
            redis_client=mock_redis,
        )

    tv_lib = local_base / settings.directories.tv / "Show" / "Season 1"
    existing_files = [f.name for f in tv_lib.glob("*.mkv")]
    assert "Show - S01E01 - Pilot.mkv" in existing_files
    assert "Show - S01E02 - Pilot.mkv" in existing_files


@pytest.mark.asyncio
async def test_pipeline_readonly_destination(
    settings: Settings,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    mock_db: unittest.mock.AsyncMock,
    mock_redis: unittest.mock.AsyncMock,
) -> None:
    local_base = pathlib.Path(settings.directories.local)
    torrent_dir = local_base / settings.directories.download / "Test.Movie"
    torrent_dir.mkdir(parents=True)
    (torrent_dir / "Movie.2023.mkv").touch()

    mock_qbt = unittest.mock.MagicMock()
    mock_qbt.torrents_files.return_value = [{"name": "Test.Movie/Movie.2023.mkv"}]
    movie_db_stub.results = [
        unittest.mock.MagicMock(original_title="Movie", release_date="2023-01-01")
    ]

    # Make destination read-only
    movies_dir = local_base / settings.directories.movie
    movies_dir.mkdir(parents=True, exist_ok=True)
    movies_dir.chmod(0o555)

    mock_add_patch = unittest.mock.patch(
        "moviedb_manager.services.pipeline.add_and_wait_for_completion"
    )
    with mock_add_patch as mock_add:
        mock_add.return_value = TorrentInfo(
            hash="h1",
            name="Test.Movie",
            data_root="Test.Movie",
            magnet_uri="magnet:?xt=urn:btih:h1",
            files=["Test.Movie/Movie.2023.mkv"],
        )
        with pytest.raises(PermissionError):
            await process_torrent_pipeline(
                qbt_client=mock_qbt,
                magnet_uri="magnet:?xt=urn:btih:h1",
                media_type="movie",
                settings=settings,
                movie_db=movie_db_stub,
                tv_db=tv_db_stub,
                db=mock_db,
                redis_client=mock_redis,
            )
    movies_dir.chmod(0o777)
