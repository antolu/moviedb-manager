from __future__ import annotations

import unittest.mock

import pytest

from moviedb_manager.services.metadata import (
    resolve_movie_title,
    resolve_tv_episode_title,
)
from moviedb_manager.services.naming import ParsedFilename

from .conftest import (
    StubMovieDbClient,
    StubMovieResult,
    StubTvDbClient,
)


@pytest.mark.asyncio
async def test_resolve_movie_title_year_match(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
        StubMovieResult(
            original_title="Interstellar: Extended", release_date="2015-05-01"
        ),
    ]
    parsed = ParsedFilename(name="Interstellar", year="2014")
    assert await resolve_movie_title(parsed, movie_db_stub) == "Interstellar (2014)"


@pytest.mark.asyncio
async def test_resolve_movie_title_no_year_match(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Interstellar", release_date="2014-11-07"),
    ]
    parsed = ParsedFilename(name="Interstellar", year="1999")
    assert await resolve_movie_title(parsed, movie_db_stub) == "Interstellar (2014)"


@pytest.mark.asyncio
async def test_resolve_movie_title_no_results(movie_db_stub: StubMovieDbClient) -> None:
    movie_db_stub.results = []
    parsed = ParsedFilename(name="Obscure Film", year="2020")
    assert await resolve_movie_title(parsed, movie_db_stub) == "Obscure Film (2020)"


@pytest.mark.asyncio
async def test_resolve_movie_title_no_year_in_parsed(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="The Matrix", release_date="1999-03-31"),
    ]
    parsed = ParsedFilename(name="The Matrix", year="")
    assert await resolve_movie_title(parsed, movie_db_stub) == "The Matrix (1999)"


@pytest.mark.asyncio
async def test_resolve_movie_title_empty_release_date(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(original_title="Unknown Film", release_date=""),
    ]
    parsed = ParsedFilename(name="Unknown Film", year="")
    assert await resolve_movie_title(parsed, movie_db_stub) == "Unknown Film"


@pytest.mark.asyncio
async def test_resolve_movie_title_strips_colon(
    movie_db_stub: StubMovieDbClient,
) -> None:
    movie_db_stub.results = [
        StubMovieResult(
            original_title="Mission: Impossible", release_date="1996-05-22"
        ),
    ]
    parsed = ParsedFilename(name="Mission Impossible", year="1996")
    title = await resolve_movie_title(parsed, movie_db_stub)
    assert ":" not in title
    assert "Mission" in title


@pytest.mark.asyncio
async def test_resolve_tv_episode_title(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [{"id": 1, "name": "The Mandalorian"}]
    tv_db_stub.series_name = "The Mandalorian"
    tv_db_stub.episode_name = "The Heiress"

    parsed = ParsedFilename(name="Mandalorian", season=2, episode=3)
    title, series_name = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert title == "The Mandalorian - S02E03 - The Heiress"
    assert series_name == "The Mandalorian"


@pytest.mark.asyncio
async def test_resolve_tv_episode_title_no_search_results(
    tv_db_stub: StubTvDbClient,
) -> None:
    tv_db_stub.search_results = []
    parsed = ParsedFilename(name="Mystery Show", season=1, episode=1)
    title, series_name = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert title == "Mystery Show"
    assert series_name == "Unknown Show"


@pytest.mark.asyncio
async def test_resolve_tv_episode_title_no_episodes(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [{"id": 1, "name": "Some Show"}]
    tv_db_stub.series_name = "Some Show"
    tv_db_stub.episode_name = "Unknown Episode"

    parsed = ParsedFilename(name="Some Show", season=1, episode=1)
    title, _ = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert "Unknown Episode" in title


@pytest.mark.asyncio
async def test_resolve_tv_episode_title_defaults_season_episode(
    tv_db_stub: StubTvDbClient,
) -> None:
    tv_db_stub.search_results = [{"id": 1, "name": "Show"}]
    tv_db_stub.series_name = "Show"
    tv_db_stub.episode_name = "Pilot"

    parsed = ParsedFilename(name="Show", season=None, episode=None)
    title, _ = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert "S01E01" in title


@pytest.mark.asyncio
async def test_resolve_tv_episode_title_strips_colon(
    tv_db_stub: StubTvDbClient,
) -> None:
    tv_db_stub.search_results = [{"id": 1, "name": "Show: Drama"}]
    tv_db_stub.series_name = "Show: Drama"
    tv_db_stub.episode_name = "Pilot: Part 1"

    parsed = ParsedFilename(name="Show Drama", season=1, episode=1)
    title, _series_name = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert ":" not in title


@pytest.mark.asyncio
async def test_resolve_tv_episode_title_utf8(tv_db_stub: StubTvDbClient) -> None:
    tv_db_stub.search_results = [{"id": 1, "name": "Über Show"}]
    tv_db_stub.series_name = "Über Show"
    tv_db_stub.episode_name = "Spécial"

    parsed = ParsedFilename(name="Uber Show", season=1, episode=1)
    title, _ = await resolve_tv_episode_title(parsed, tv_db_stub)

    assert "Über Show" in title
    assert "Spécial" in title


@pytest.mark.asyncio
async def test_resolve_movie_title_api_failure(
    movie_db_stub: StubMovieDbClient,
) -> None:
    parsed = ParsedFilename(name="Interstellar", year="2014")

    with (
        unittest.mock.patch.object(
            movie_db_stub, "search", side_effect=RuntimeError("API Down")
        ),
        pytest.raises(RuntimeError, match="API Down"),
    ):
        await resolve_movie_title(parsed, movie_db_stub)


@pytest.mark.asyncio
async def test_resolve_tv_title_api_failure(tv_db_stub: StubTvDbClient) -> None:
    parsed = ParsedFilename(name="The Boys", season=1, episode=1)

    with (
        unittest.mock.patch.object(
            tv_db_stub, "search_series", side_effect=RuntimeError("TVDB Down")
        ),
        pytest.raises(RuntimeError, match="TVDB Down"),
    ):
        await resolve_tv_episode_title(parsed, tv_db_stub)
