from pathlib import Path
from unittest.mock import MagicMock

import moviedb_manager.config.settings
import moviedb_manager.services.pipeline
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
) -> None:
    # Setup stubs
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07")
    ]

    # Mock qBittorrent client
    qbt_mock = MagicMock()
    # add_and_wait_for_completion is called inside, but we need to mock the functions it calls if we don't mock the whole service
    # Alternatively, we could mock add_and_wait_for_completion itself if it was injected,
    # but here it's imported. Let's mock the qbt_client methods.

    qbt_mock.torrents_add.return_value = "Ok."
    qbt_mock.torrents_info.side_effect = [
        [
            {"hash": "h1", "name": "Interstellar.2014.1080p", "magnet_uri": "mag1"}
        ],  # first call to find
        [{"state": "uploading"}],  # while loop
        [{"state": "uploading", "hash": "h1"}],  # final info
    ]
    qbt_mock.torrents_files.return_value = [
        {"name": "Interstellar.2014.1080p/movie.mkv"}
    ]

    settings = moviedb_manager.config.settings.Settings()
    settings.directories.local = str(media_root)
    settings.directories.remote = str(media_root)

    # Create the actual file that find_media_files will find
    download_path = media_root / "downloads" / "Interstellar.2014.1080p"
    download_path.mkdir(parents=True, exist_ok=True)
    mkv_file = download_path / "movie.mkv"
    mkv_file.touch()

    moviedb_manager.services.pipeline.process_torrent_pipeline(
        magnet_uri="mag1",
        media_type="movie",
        qbt_client=qbt_mock,
        movie_db=movie_db_stub,
        tv_db=tv_db_stub,
        settings=settings,
    )

    # Verify file was moved to movie library
    movie_lib = media_root / "movies"
    assert (movie_lib / "Interstellar (2014).mkv").exists()
    assert not download_path.exists()


def test_process_tv_pipeline(
    media_root: Path,
    movie_db_stub: StubMovieDbClient,
    tv_db_stub: StubTvDbClient,
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
        [{"state": "uploading"}],
        [{"state": "uploading", "hash": "h2"}],
    ]
    qbt_mock.torrents_files.return_value = [{"name": "Mandalorian.S02E05/ep.mp4"}]

    settings = moviedb_manager.config.settings.Settings()
    settings.directories.local = str(media_root)
    settings.directories.remote = str(media_root)

    # Create the actual file
    download_path = media_root / "downloads" / "Mandalorian.S02E05"
    download_path.mkdir(parents=True, exist_ok=True)
    mp4_file = download_path / "The.Mandalorian.S02E05.720p.mp4"
    mp4_file.touch()

    moviedb_manager.services.pipeline.process_torrent_pipeline(
        magnet_uri="mag2",
        media_type="tv",
        qbt_client=qbt_mock,
        movie_db=movie_db_stub,
        tv_db=tv_db_stub,
        settings=settings,
    )

    # Verify file was moved to TV library
    tv_lib = media_root / "tv" / "The Mandalorian" / "Season 2"
    assert (tv_lib / "The Mandalorian - S02E05 - The Jedi.mp4").exists()
    assert not download_path.exists()
