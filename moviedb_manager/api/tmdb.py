from __future__ import annotations

import tmdbv3api


class TmdbMovieAdapter:
    def __init__(self, api_key: str) -> None:
        self._tmdb = tmdbv3api.TMDb()
        self._tmdb.api_key = api_key
        self._movie = tmdbv3api.Movie()

    def search(self, name: str) -> list[tmdbv3api.objs.movie.Movie]:
        results = self._movie.search(name)
        if isinstance(results, list):
            return results
        return getattr(results, "results", [])
