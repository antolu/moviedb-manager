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


def test_resolve_movie_title_year_match(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
        StubMovieResult(
            original_title="Interstellar: Extended", release_date="2015-05-01"
        ),
    ]
    parsed = ParsedFilename(name="Interstellar", year="2014")
    assert resolve_movie_title(parsed, movie_db_stub) == "Interstellar (2014)"


def test_resolve_movie_title_no_year_match(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
    ]
    parsed = ParsedFilename(name="Interstellar", year="1999")
    assert resolve_movie_title(parsed, movie_db_stub) == "Interstellar (2014)"


def test_resolve_movie_title_no_results(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = []
    parsed = ParsedFilename(name="Obscure Film", year="2020")
    assert resolve_movie_title(parsed, movie_db_stub) == "Obscure Film"


def test_resolve_movie_title_no_year_in_parsed(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="The Matrix", release_date="1999-03-31"),
    ]
    parsed = ParsedFilename(name="The Matrix", year="")
    assert resolve_movie_title(parsed, movie_db_stub) == "The Matrix (1999)"


def test_resolve_movie_title_empty_release_date(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Unknown Film", release_date=""),
    ]
    parsed = ParsedFilename(name="Unknown Film", year="")
    assert resolve_movie_title(parsed, movie_db_stub) == "Unknown Film"


def test_resolve_movie_title_strips_colon(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(
            original_title="Mission: Impossible", release_date="1996-05-22"
        ),
    ]
    parsed = ParsedFilename(name="Mission Impossible", year="1996")
    title = resolve_movie_title(parsed, movie_db_stub)
    assert ":" not in title
    assert "Mission" in title


def test_resolve_tv_episode_title(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="The Mandalorian")]
    tv_db_stub.series_info = {"seriesName": "The Mandalorian"}
    tv_db_stub.episodes = [{"episodeName": "The Heiress"}]

    parsed = ParsedFilename(name="Mandalorian", season=2, episode=3)
    title, series_name = resolve_tv_episode_title(parsed, tv_db_stub)

    assert title == "The Mandalorian - S02E03 - The Heiress"
    assert series_name == "The Mandalorian"


def test_resolve_tv_episode_title_no_search_results(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = []
    parsed = ParsedFilename(name="Mystery Show", season=1, episode=1)
    title, series_name = resolve_tv_episode_title(parsed, tv_db_stub)

    assert title == "Mystery Show"
    assert series_name == "Unknown Show"


def test_resolve_tv_episode_title_no_episodes(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="Some Show")]
    tv_db_stub.series_info = {"seriesName": "Some Show"}
    tv_db_stub.episodes = []

    parsed = ParsedFilename(name="Some Show", season=1, episode=1)
    title, _ = resolve_tv_episode_title(parsed, tv_db_stub)

    assert "Unknown Episode" in title


def test_resolve_tv_episode_title_defaults_season_episode(
    tv_db_stub: StubTvDbClient,
) -> None:
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="Show")]
    tv_db_stub.series_info = {"seriesName": "Show"}
    tv_db_stub.episodes = [{"episodeName": "Pilot"}]

    parsed = ParsedFilename(name="Show", season=None, episode=None)
    title, _ = resolve_tv_episode_title(parsed, tv_db_stub)

    assert "S01E01" in title


def test_resolve_tv_episode_title_strips_colon(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [StubTvShowResult(id=1, series_name="Show: Drama")]
    tv_db_stub.series_info = {"seriesName": "Show: Drama"}
    tv_db_stub.episodes = [{"episodeName": "Pilot: Part 1"}]

    parsed = ParsedFilename(name="Show Drama", season=1, episode=1)
    title, _series_name = resolve_tv_episode_title(parsed, tv_db_stub)

    assert ":" not in title
