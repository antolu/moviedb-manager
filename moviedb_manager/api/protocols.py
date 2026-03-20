from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MovieSearchResult(Protocol):
    original_title: str
    release_date: str  # "YYYY-MM-DD"


@runtime_checkable
class MovieDbClient(Protocol):
    def search(self, name: str) -> list[MovieSearchResult]: ...


@runtime_checkable
class TvShowResult(Protocol):
    id: int
    series_name: str


@runtime_checkable
class TvSearchResult(Protocol):
    def series(self, name: str) -> list[TvShowResult]: ...


@runtime_checkable
class TvDbClient(Protocol):
    def Search(self) -> TvSearchResult: ...  # noqa: N802

    def Series(self, tv_id: int) -> Any: ...  # noqa: N802
