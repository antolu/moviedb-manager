from __future__ import annotations

import pathlib
import typing

from ..models.media import EpisodeInfo, MediaType
from .fileops import cleanup_directory, find_media_files, move_file, rename_file
from .metadata import resolve_movie_title, resolve_tv_episode_title
from .naming import parse_filename
from .torrent import add_and_wait_for_completion

if typing.TYPE_CHECKING:
    import qbittorrentapi

    from ..api.protocols import MovieDbClient, TvDbClient
    from ..config.settings import Settings


def process_torrent_pipeline(  # noqa: PLR0913
    magnet_uri: str,
    media_type: MediaType,
    *,
    qbt_client: qbittorrentapi.Client,
    movie_db: MovieDbClient,
    tv_db: TvDbClient,
    settings: Settings,
) -> None:
    dirs = settings.directories
    remote_download_path = pathlib.Path(dirs.remote) / dirs.download

    # 1. Download
    torrent_info = add_and_wait_for_completion(
        qbt_client, magnet_uri, remote_download_path
    )

    # 2. Find files
    local_download_path = (
        pathlib.Path(dirs.local) / dirs.download / torrent_info.data_root
    )
    media_files = find_media_files(
        local_download_path, settings.misc.mediaextensions, media_type
    )

    if not media_files:
        msg = f"No media files found in {local_download_path}"
        raise RuntimeError(msg)

    # 3. Process each file
    for media_file in media_files:
        parsed = parse_filename(media_file.filename, media_type)

        if media_type == "movie":
            real_name = resolve_movie_title(parsed, movie_db)
            dest_dir = pathlib.Path(dirs.local) / dirs.movie
        else:
            real_name, series_name = resolve_tv_episode_title(parsed, tv_db)
            media_file.episode_info = EpisodeInfo(
                season=parsed.season or 1, episode=parsed.episode or 1
            )
            dest_dir = (
                pathlib.Path(dirs.local)
                / dirs.tv
                / series_name
                / f"Season {media_file.episode_info.season}"
            )

        # 4. Rename and move
        rename_file(media_file, real_name)
        move_file(media_file, dest_dir)

    # 5. Cleanup
    cleanup_directory(local_download_path)
