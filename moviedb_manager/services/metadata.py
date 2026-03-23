from __future__ import annotations

import asyncio
import typing

if typing.TYPE_CHECKING:
    from ..api.protocols import MovieDbClient, TvDbClient
    from .naming import ParsedFilename


async def resolve_movie_title(
    parsed: ParsedFilename,
    client: MovieDbClient,
) -> str:
    results = await asyncio.to_thread(client.search, parsed.name)
    if not results:
        year_suffix = f" ({parsed.year})" if parsed.year else ""
        return f"{parsed.name}{year_suffix}"

    metadata = None
    if parsed.year:
        for item in results:
            if item.release_date.startswith(parsed.year):
                metadata = item
                break

    if metadata is None:
        metadata = results[0]

    year_suffix = (
        f" ({metadata.release_date.split('-')[0]})" if metadata.release_date else ""
    )
    title = f"{metadata.original_title}{year_suffix}"
    return title.replace(r":", "")


async def resolve_tv_episode_title(
    parsed: ParsedFilename,
    client: TvDbClient,
) -> tuple[str, str]:
    results = await asyncio.to_thread(client.search_series, parsed.name)
    if not results:
        return parsed.name, "Unknown Show"

    series_id = results[0]["id"]
    season = parsed.season or 1
    episode = parsed.episode or 1

    series_name = await asyncio.to_thread(client.get_series_name, series_id)
    episode_name = await asyncio.to_thread(
        client.get_episode_name, series_id, season, episode
    )

    episode_code = f"S{season:02d}E{episode:02d}"
    title = f"{series_name} - {episode_code} - {episode_name}"
    return title.replace(r":", ""), series_name
