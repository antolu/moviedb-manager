from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import moviedb_manager.config.settings
from moviedb_manager.api.protocols import MovieSearchResult, TvShowResult

if TYPE_CHECKING:
    pass


@dataclass
class StubMovieResult:
    original_title: str
    release_date: str


class StubMovieDbClient:
    def __init__(self, results: list[MovieSearchResult] | None = None) -> None:
        self.results = results or []

    def search(self, name: str) -> list[MovieSearchResult]:
        return self.results


@dataclass
class StubTvShowResult:
    id: int
    series_name: str


class StubTvDbClient:
    class StubSearch:
        def __init__(self, results: list[TvShowResult]) -> None:
            self.results = results

        def series(self, name: str) -> list[TvShowResult]:
            return self.results

    class StubSeries:
        def __init__(
            self, info: dict[str, str], episodes: list[dict[str, str]]
        ) -> None:
            self._info = info
            self._episodes = episodes
            self.Episodes = self.StubEpisodes(episodes)

        class StubEpisodes:
            def __init__(self, episodes: list[dict[str, str]]) -> None:
                self.episodes = episodes

            def update_filters(self, **kwargs: Any) -> None:
                pass

            def all(self) -> list[dict[str, str]]:
                return self.episodes

        def info(self) -> dict[str, str]:
            return self._info

    def __init__(
        self,
        search_results: list[TvShowResult] | None = None,
        series_info: dict[str, str] | None = None,
        episodes: list[dict[str, str]] | None = None,
    ) -> None:
        self.search_results = search_results or []
        self.series_info = series_info or {"seriesName": "Default Show"}
        self.episodes = episodes or [{"episodeName": "Default Episode"}]

    def Search(self) -> StubSearch:  # noqa: N802
        return self.StubSearch(self.search_results)

    def Series(self, tv_id: int) -> StubSeries:  # noqa: N802
        return self.StubSeries(self.series_info, self.episodes)


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
