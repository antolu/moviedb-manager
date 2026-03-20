from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import moviedb_manager.models.media
import moviedb_manager.services.fileops
import moviedb_manager.services.metadata
import moviedb_manager.services.naming
import moviedb_manager.services.torrent

if TYPE_CHECKING:
    from qbittorrentapi import Client

    import moviedb_manager.api.protocols
    import moviedb_manager.config.settings


def process_torrent_pipeline(  # noqa: PLR0913
    magnet_uri: str,
    media_type: moviedb_manager.models.media.MediaType,
    *,
    qbt_client: Client,
    movie_db: moviedb_manager.api.protocols.MovieDbClient,
    tv_db: moviedb_manager.api.protocols.TvDbClient,
    settings: moviedb_manager.config.settings.Settings,
) -> None:
    dirs = settings.directories
    remote_download_path = Path(dirs.remote) / dirs.download

    # 1. Download
    torrent_info = moviedb_manager.services.torrent.add_and_wait_for_completion(
        qbt_client, magnet_uri, remote_download_path
    )

    # 2. Find files
    local_download_path = Path(dirs.local) / dirs.download / torrent_info.data_root
    media_files = moviedb_manager.services.fileops.find_media_files(
        local_download_path, settings.misc.mediaextensions, media_type
    )

    if not media_files:
        msg = f"No media files found in {local_download_path}"
        raise RuntimeError(msg)

    # 3. Process each file
    for media_file in media_files:
        parsed = moviedb_manager.services.naming.parse_filename(
            media_file.filename, media_type
        )

        if media_type == "movie":
            real_name = moviedb_manager.services.metadata.resolve_movie_title(
                parsed, movie_db
            )
            dest_dir = Path(dirs.local) / dirs.movie
        else:
            real_name, series_name = (
                moviedb_manager.services.metadata.resolve_tv_episode_title(
                    parsed, tv_db
                )
            )
            media_file.episode_info = moviedb_manager.models.media.EpisodeInfo(
                season=parsed.season or 1, episode=parsed.episode or 1
            )
            dest_dir = (
                Path(dirs.local)
                / dirs.tv
                / series_name
                / f"Season {media_file.episode_info.season}"
            )

        # 4. Rename and move
        moviedb_manager.services.fileops.rename_file(media_file, real_name)
        moviedb_manager.services.fileops.move_file(media_file, dest_dir)

    # 5. Cleanup
    moviedb_manager.services.fileops.cleanup_directory(local_download_path)
