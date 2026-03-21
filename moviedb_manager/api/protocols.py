from __future__ import annotations

import typing


@typing.runtime_checkable
class MovieSearchResult(typing.Protocol):
    original_title: str
    release_date: str  # "YYYY-MM-DD"


@typing.runtime_checkable
class MovieDbClient(typing.Protocol):
    def search(self, name: str) -> list[MovieSearchResult]: ...


@typing.runtime_checkable
class TvDbClient(typing.Protocol):
    def search_series(self, name: str) -> list[dict]: ...

    def get_series_name(self, series_id: int) -> str: ...

    def get_episode_name(self, series_id: int, season: int, episode: int) -> str: ...
