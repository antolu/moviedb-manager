from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MovieSearchResult(Protocol):
    original_title: str
    release_date: str  # "YYYY-MM-DD"


@runtime_checkable
class MovieDbClient(Protocol):
    def search(self, name: str) -> list[MovieSearchResult]: ...


@runtime_checkable
class TvDbClient(Protocol):
    def search_series(self, name: str) -> list[dict]: ...

    def get_series_name(self, series_id: int) -> str: ...

    def get_episode_name(self, series_id: int, season: int, episode: int) -> str: ...
