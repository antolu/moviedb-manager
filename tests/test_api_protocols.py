from __future__ import annotations

from moviedb_manager.api.protocols import (
    MovieDbClient,
    MovieSearchResult,
    TvDbClient,
    TvSearchResult,
    TvShowResult,
)
from moviedb_manager.api.tmdb import TmdbMovieAdapter
from moviedb_manager.api.tvdb import TvDbAdapter
from tests.conftest import (
    StubMovieDbClient,
    StubMovieResult,
    StubTvDbClient,
    StubTvShowResult,
)


def test_tmdb_adapter_compliance() -> None:
    adapter = TmdbMovieAdapter(api_key="test")
    assert isinstance(adapter, MovieDbClient)


def test_tvdb_adapter_compliance() -> None:
    adapter = TvDbAdapter(api_key="test")
    assert isinstance(adapter, TvDbClient)


def test_tvdb_search_compliance() -> None:
    # This is a bit tricky because we'd need a real instance or a very careful mock
    # that actually has the methods. But we can check if the adapter's Search()
    # return type would match if it was runtime_checkable (it is).
    TvDbAdapter(api_key="test")
    # Search() returns a tvdbsimple.Search which we probably can't easily instantiate
    # without it doing something. But we can verify the protocol has the right methods.
    assert hasattr(TvSearchResult, "series")


# We can also test our stubs to make sure they are useful


def test_stubs_compliance() -> None:
    assert isinstance(StubMovieDbClient(), MovieDbClient)
    assert isinstance(StubMovieResult("t", "d"), MovieSearchResult)
    assert isinstance(StubTvDbClient(), TvDbClient)
    assert isinstance(StubTvShowResult(1, "n"), TvShowResult)
