from __future__ import annotations

from unittest.mock import patch

from moviedb_manager.api.protocols import (
    MovieDbClient,
    TvDbClient,
)
from moviedb_manager.api.tmdb import TmdbMovieAdapter
from moviedb_manager.api.tvdb import TvDbAdapter
from tests.conftest import (
    StubMovieDbClient,
    StubMovieResult,
    StubTvDbClient,
)


def test_tmdb_adapter_compliance() -> None:
    adapter = TmdbMovieAdapter(api_key="test")
    assert isinstance(adapter, MovieDbClient)


def test_tvdb_adapter_compliance() -> None:
    with patch("tvdb_v4_official.Auth") as mock_auth:
        mock_auth.return_value.get_token.return_value = "fake-token"
        adapter = TvDbAdapter(api_key="test")
    assert isinstance(adapter, TvDbClient)


def test_stubs_compliance() -> None:
    assert isinstance(StubMovieDbClient(), MovieDbClient)
    assert isinstance(StubMovieResult("t", "d"), object)
    assert isinstance(StubTvDbClient(), TvDbClient)
