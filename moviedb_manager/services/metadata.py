from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import moviedb_manager.api.protocols
    import moviedb_manager.services.naming


def resolve_movie_title(
    parsed: moviedb_manager.services.naming.ParsedFilename,
    client: moviedb_manager.api.protocols.MovieDbClient,
) -> str:
    results = client.search(parsed.name)
    if not results:
        return parsed.name

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


def resolve_tv_episode_title(
    parsed: moviedb_manager.services.naming.ParsedFilename,
    client: moviedb_manager.api.protocols.TvDbClient,
) -> tuple[str, str]:
    search = client.Search()
    results = search.series(parsed.name)
    if not results:
        return parsed.name, "Unknown Show"

    tv_id = results[0].id
    show = client.Series(tv_id)

    season = parsed.season or 1
    episode = parsed.episode or 1

    show.Episodes.update_filters(airedSeason=season, airedEpisode=episode)
    episodes = show.Episodes.all()

    episode_name = episodes[0]["episodeName"] if episodes else "Unknown Episode"
    show_info = show.info()
    series_name = show_info["seriesName"]

    episode_code = f"S{season:02d}E{episode:02d}"
    title = f"{series_name} - {episode_code} - {episode_name}"
    return title.replace(r":", ""), series_name
