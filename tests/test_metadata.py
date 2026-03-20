from __future__ import annotations

from moviedb_manager.services.metadata import (
    resolve_movie_title,
    resolve_tv_episode_title,
)
from moviedb_manager.services.naming import ParsedFilename
from tests.conftest import (
    StubMovieDbClient,
    StubMovieResult,
    StubTvDbClient,
    StubTvShowResult,
)


def test_resolve_movie_title(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
        StubMovieResult(
            original_title="Interstellar: Extended", release_date="2015-05-01"
        ),
    ]

    parsed = ParsedFilename(name="Interstellar", year="2014")
    title = resolve_movie_title(parsed, movie_db_stub)

    assert title == "Interstellar (2014)"


def test_resolve_movie_title_no_year_match(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
    ]

    parsed = ParsedFilename(name="Interstellar", year="1999")
    title = resolve_movie_title(parsed, movie_db_stub)

    assert title == "Interstellar (2014)"  # Fallback to first result


def test_resolve_tv_episode_title(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="The Mandalorian")]
    tv_db_stub.series_info = {"seriesName": "The Mandalorian"}
    tv_db_stub.episodes = [{"episodeName": "The Heiress"}]

    parsed = ParsedFilename(name="Mandalorian", season=2, episode=3)
    title, series_name = resolve_tv_episode_title(parsed, tv_db_stub)

    assert title == "The Mandalorian - S02E03 - The Heiress"
    assert series_name == "The Mandalorian"
