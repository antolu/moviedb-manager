from __future__ import annotations

import tvdb_v4_official


class TvDbAdapter:
    def __init__(self, api_key: str) -> None:
        self._client = tvdb_v4_official.TVDB(api_key)

    def search_series(self, name: str) -> list[dict]:
        return self._client.search(name, type="series")

    def get_series_name(self, series_id: int) -> str:
        series = self._client.get_series(series_id)
        return series["name"]

    def get_episode_name(self, series_id: int, season: int, episode: int) -> str:
        data = self._client.get_series_episodes(series_id, page=0)
        episodes = data.get("episodes") or []
        for ep in episodes:
            if ep.get("seasonNumber") == season and ep.get("number") == episode:
                return ep.get("name") or "Unknown Episode"
        return "Unknown Episode"
