from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import moviedb_manager.config.settings
from moviedb_manager.api.protocols import MovieSearchResult


@dataclass
class StubMovieResult:
    original_title: str
    release_date: str


class StubMovieDbClient:
    def __init__(self, results: list[MovieSearchResult] | None = None) -> None:
        self.results = results or []

    def search(self, name: str) -> list[MovieSearchResult]:
        return self.results


class StubTvDbClient:
    search_results: list[dict]
    series_name: str
    episode_name: str

    def __init__(
        self,
        search_results: list[dict] | None = None,
        series_name: str = "Default Show",
        episode_name: str = "Default Episode",
    ) -> None:
        self.search_results = search_results or []
        self.series_name = series_name
        self.episode_name = episode_name

    def search_series(self, name: str) -> list[dict]:
        return self.search_results

    def get_series_name(self, series_id: int) -> str:
        return self.series_name

    def get_episode_name(self, series_id: int, season: int, episode: int) -> str:
        return self.episode_name


@pytest.fixture
def movie_db_stub() -> StubMovieDbClient:
    return StubMovieDbClient()


@pytest.fixture
def tv_db_stub() -> StubTvDbClient:
    return StubTvDbClient()


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()

    (download_dir / "Movie.2023.1080p.mkv").touch()

    tv_dir = download_dir / "Show.S01E05.720p"
    tv_dir.mkdir()
    (tv_dir / "file.mp4").touch()

    return tmp_path


@pytest.fixture
def settings(tmp_path: Path) -> moviedb_manager.config.settings.Settings:
    s = moviedb_manager.config.settings.Settings()
    s.directories.local = str(tmp_path)
    s.directories.remote = str(tmp_path)
    return s
