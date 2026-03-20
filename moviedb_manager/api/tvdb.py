from __future__ import annotations

import tvdbsimple


class TvDbAdapter:
    def __init__(self, api_key: str) -> None:
        tvdbsimple.KEYS.API_KEY = api_key

    def Search(self) -> tvdbsimple.Search:  # noqa: N802, PLR6301
        return tvdbsimple.Search()

    def Series(self, tv_id: int) -> tvdbsimple.Series:  # noqa: N802, PLR6301
        return tvdbsimple.Series(tv_id)
