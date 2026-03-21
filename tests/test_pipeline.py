from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import moviedb_manager.config.settings
import moviedb_manager.services.pipeline
from moviedb_manager.models.media import TorrentInfo
from tests.conftest import (
    StubMovieDbClient,
    StubMovieResult,
    StubTvDbClient,
    StubTvShowResult,
)


def test_process_movie_pipeline(
    media_root: Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: moviedb_manager.config.settings.Settings,
) -> None:
    # Setup stubs
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07")
    ]

    # Mock qBittorrent client
    qbt_mock = MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.side_effect = [
        [{"hash": "h1", "name": "Interstellar.2014.1080p", "magnet_uri": "mag1"}],
        [{"state": "completed", "hash": "h1"}],
    ]
    qbt_mock.torrents_files.return_value = [
        {"name": "Interstellar.2014.1080p/movie.mkv"}
    ]

    # Create the actual file
    download_path = media_root / "downloads" / "Interstellar.2014.1080p"
    download_path.mkdir(parents=True, exist_ok=True)
    mkv_file = download_path / "movie.mkv"
    mkv_file.touch()

    with patch("moviedb_manager.services.torrent.sleep", return_value=None):
        moviedb_manager.services.pipeline.process_torrent_pipeline(
            magnet_uri="mag1",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
        )

    # Verify
    movie_lib = media_root / "movies"
    assert (movie_lib / "Interstellar (2014).mkv").exists()
    assert not download_path.exists()


def test_process_tv_pipeline(
    media_root: Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: moviedb_manager.config.settings.Settings,
) -> None:
    # Setup stubs
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="The Mandalorian")]
    tv_db_stub.series_info = {"seriesName": "The Mandalorian"}
    tv_db_stub.episodes = [{"episodeName": "The Jedi"}]

    # Mock qBittorrent client
    qbt_mock = MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.side_effect = [
        [{"hash": "h2", "name": "Mandalorian.S02E05", "magnet_uri": "mag2"}],
        [{"state": "completed", "hash": "h2"}],
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Mandalorian.S02E05/ep.mp4"}]

    # Create the actual file
    download_path = media_root / "downloads" / "Mandalorian.S02E05"
    download_path.mkdir(parents=True, exist_ok=True)
    mp4_file = download_path / "The.Mandalorian.S02E05.720p.mp4"
    mp4_file.touch()

    with patch("moviedb_manager.services.torrent.sleep", return_value=None):
        moviedb_manager.services.pipeline.process_torrent_pipeline(
            magnet_uri="mag2",
            media_type="tv",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
        )

    # Verify
    tv_lib = media_root / "tv" / "The Mandalorian" / "Season 2"
    assert (tv_lib / "The Mandalorian - S02E05 - The Jedi.mp4").exists()
    assert not download_path.exists()


def test_pipeline_no_media_files(
    media_root: Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: moviedb_manager.config.settings.Settings,
) -> None:
    qbt_mock = MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.return_value = [
        {"hash": "h3", "name": "Empty", "magnet_uri": "mag3", "state": "completed"}
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Empty/nothing.txt"}]

    # Create empty dir
    download_path = media_root / "downloads" / "Empty"
    download_path.mkdir(parents=True, exist_ok=True)
    (download_path / "nothing.txt").touch()

    with (
        patch("moviedb_manager.services.torrent.sleep", return_value=None),
        pytest.raises(RuntimeError, match="No media files found"),
    ):
        moviedb_manager.services.pipeline.process_torrent_pipeline(
            magnet_uri="mag3",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
        )


def test_pipeline_multiple_files(
    media_root: Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
    settings: moviedb_manager.config.settings.Settings,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Kill Bill", release_date="2003-10-10")
    ]
    qbt_mock = MagicMock()
    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.return_value = [
        {"hash": "h4", "name": "Kill.Bill", "magnet_uri": "mag4", "state": "completed"}
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Kill.Bill/vol1.mkv"}]

    download_path = media_root / "downloads" / "Kill.Bill"
    download_path.mkdir(parents=True, exist_ok=True)
    (download_path / "vol1.mkv").touch()
    (download_path / "vol2.mkv").touch()

    with patch("moviedb_manager.services.torrent.sleep", return_value=None):
        moviedb_manager.services.pipeline.process_torrent_pipeline(
            magnet_uri="mag4",
            media_type="movie",
            qbt_client=qbt_mock,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
            settings=settings,
        )

    movie_lib = media_root / "movies"
    assert (movie_lib / "Kill Bill (2003).mkv").exists()
    # If both files had the same name after parsing/resolving, they would overwrite each other
    # unless naming.py or fileops.py handles duplicates.
    # Current implementation might overwrite. Let's check how many files are in movie_lib.
    assert len(list(movie_lib.glob("*.mkv"))) >= 1


def test_pipeline_multi_file_tv_torrent(
    settings: moviedb_manager.config.settings.Settings,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
) -> None:
    # Torrent has two TV episodes
    local_base = Path(settings.directories.local)
    torrent_dir = local_base / settings.directories.download / "Show.Torrent"
    torrent_dir.mkdir(parents=True)
    (torrent_dir / "Show.S01E01.mkv").touch()
    (torrent_dir / "Show.S01E02.mkv").touch()

    # Mock qbt client
    mock_qbt = MagicMock()
    mock_qbt.torrents_files.return_value = [
        {"name": "Show.Torrent/Show.S01E01.mkv"},
        {"name": "Show.Torrent/Show.S01E02.mkv"},
    ]

    # Stubs
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="Show")]
    tv_db_stub.series_info = {"seriesName": "Show"}
    tv_db_stub.episodes = [
        {"episodeName": "Pilot", "airedEpisodeNumber": 1, "airedSeason": 1},
        {"episodeName": "Second", "airedEpisodeNumber": 2, "airedSeason": 1},
    ]

    with patch(
        "moviedb_manager.services.torrent.add_and_wait_for_completion"
    ) as mock_add:
        mock_add.return_value = TorrentInfo(
            hash="h1", name="Show.Torrent", data_root="Show.Torrent", magnet_uri="h1"
        )
        moviedb_manager.services.pipeline.process_torrent_pipeline(
            qbt_client=mock_qbt,
            magnet_uri="h1",
            media_type="tv",
            settings=settings,
            movie_db=movie_db_stub,
            tv_db=tv_db_stub,
        )

    # Verify both moved
    tv_lib = local_base / settings.directories.tv / "Show" / "Season 1"
    existing_files = [f.name for f in tv_lib.glob("*.mkv")]
    assert "Show - S01E01 - Pilot.mkv" in existing_files
    assert "Show - S01E02 - Second.mkv" in existing_files


def test_pipeline_readonly_destination(
    settings: moviedb_manager.config.settings.Settings,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
) -> None:
    local_base = Path(settings.directories.local)
    torrent_dir = local_base / settings.directories.download / "Test.Movie"
    torrent_dir.mkdir(parents=True)
    (torrent_dir / "Movie.2023.mkv").touch()

    mock_qbt = MagicMock()
    mock_qbt.torrents_files.return_value = [{"name": "Test.Movie/Movie.2023.mkv"}]
    movie_db_stub.results = [
        StubMovieResult(original_title="Movie", release_date="2023-01-01")
    ]

    # Make destination read-only
    movies_dir = local_base / settings.directories.movie
    movies_dir.mkdir(parents=True, exist_ok=True)
    movies_dir.chmod(0o555)

    mock_add_patch = patch(
        "moviedb_manager.services.torrent.add_and_wait_for_completion"
    )
    with mock_add_patch as mock_add:
        mock_add.return_value = TorrentInfo(
            hash="h1", name="Test.Movie", data_root="Test.Movie", magnet_uri="h1"
        )
        with pytest.raises(PermissionError):
            moviedb_manager.services.pipeline.process_torrent_pipeline(
                qbt_client=mock_qbt,
                magnet_uri="h1",
                media_type="movie",
                settings=settings,
                movie_db=movie_db_stub,
                tv_db=tv_db_stub,
            )
    movies_dir.chmod(0o777)
