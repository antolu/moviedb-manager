from __future__ import annotations

import unittest.mock

from moviedb_manager.api.tmdb import TmdbMovieAdapter
from moviedb_manager.api.tvdb import TvDbAdapter


def test_tmdb_adapter_search() -> None:
    with (
        unittest.mock.patch("tmdbv3api.TMDb"),
        unittest.mock.patch("tmdbv3api.Movie") as mock_movie_cls,
    ):
        mock_movie = mock_movie_cls.return_value
        # Case 1: list returned
        mock_movie.search.return_value = ["movie1"]
        adapter = TmdbMovieAdapter("key")
        assert adapter.search("test") == ["movie1"]

        # Case 2: non-list returned
        mock_movie.search.return_value = None
        assert adapter.search("test") == []


def test_tvdb_adapter_methods() -> None:
    with unittest.mock.patch("tvdb_v4_official.TVDB") as mock_tvdb_cls:
        mock_client = mock_tvdb_cls.return_value
        adapter = TvDbAdapter("key")

        # test search_series
        mock_client.search.return_value = [{"id": 1}]
        assert adapter.search_series("show") == [{"id": 1}]

        # test get_series_name
        mock_client.get_series.return_value = {"name": "ShowName"}
        assert adapter.get_series_name(1) == "ShowName"

        # test get_episode_name
        mock_client.get_series_episodes.return_value = {
            "episodes": [
                {"seasonNumber": 1, "number": 1, "name": "Ep1"},
                {"seasonNumber": 1, "number": 2, "name": None},
            ]
        }
        # Case 1: found
        assert adapter.get_episode_name(1, 1, 1) == "Ep1"
        # Case 2: found but name is None
        assert adapter.get_episode_name(1, 1, 2) == "Unknown Episode"
        # Case 3: not found
        assert adapter.get_episode_name(1, 2, 1) == "Unknown Episode"

        # Case 4: episodes is None
        mock_client.get_series_episodes.return_value = {}
        assert adapter.get_episode_name(1, 1, 1) == "Unknown Episode"
