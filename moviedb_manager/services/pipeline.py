from __future__ import annotations

import pathlib
import typing
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import Settings
from ..db.models import DownloadedFile, DownloadStatus, TorrentDownload
from ..models.media import EpisodeInfo, MediaFile, MediaType
from .fileops import cleanup_directory, move_file, rename_file
from .metadata import resolve_movie_title, resolve_tv_episode_title
from .naming import parse_filename
from .torrent import add_and_wait_for_completion

if typing.TYPE_CHECKING:
    import qbittorrentapi

    from ..api.protocols import MovieDbClient, TvDbClient


async def process_torrent_pipeline(  # noqa: PLR0913
    magnet_uri: str,
    media_type: MediaType,
    *,
    qbt_client: qbittorrentapi.Client,
    movie_db: MovieDbClient,
    tv_db: TvDbClient,
    settings: Settings,
    db: AsyncSession,
    redis_client: redis.Redis,
) -> None:
    dirs = settings.directories
    remote_download_path = pathlib.Path(dirs.remote) / dirs.download

    # 0. Create DB entry
    torrent_db = TorrentDownload(
        magnet_uri=magnet_uri, media_type=media_type, status=DownloadStatus.PENDING
    )
    db.add(torrent_db)
    await db.commit()
    await db.refresh(torrent_db)

    try:
        # 1. Download
        torrent_db.status = DownloadStatus.DOWNLOADING
        await db.commit()

        torrent_info = await add_and_wait_for_completion(
            qbt_client,
            magnet_uri,
            remote_download_path,
            torrent_id=torrent_db.id,
            redis_client=redis_client,
        )

        # Update Redis to show it's now processing (download finished)
        await typing.cast(
            typing.Awaitable[int],
            redis_client.hset(
                f"torrent:{torrent_db.id}",
                mapping={
                    "state": "processing",
                    "progress": "1.0",
                    "eta": "0",
                },
            ),
        )

        # 2. Identify files
        media_files = []
        local_torrent_base = pathlib.Path(dirs.local) / dirs.download

        for rel_path in torrent_info.files:
            abs_path = local_torrent_base / rel_path
            ext = abs_path.suffix.lower().lstrip(".")
            if ext in settings.misc.mediaextensions:
                media_files.append(
                    MediaFile(
                        filename=abs_path.name,
                        absolute_path=abs_path,
                        media_type=media_type,
                    )
                )

        if not media_files:
            msg = f"No media files found in torrent {torrent_info.name}"
            # Log specific files found vs extensions allowed if it was a real app
            raise RuntimeError(msg)

        # 3. Process each file
        for media_file in media_files:
            parsed = parse_filename(media_file.filename, media_type)

            if media_type == "movie":
                real_name = await resolve_movie_title(parsed, movie_db)
                dest_dir = pathlib.Path(dirs.local) / dirs.movie
            else:
                real_name, series_name = await resolve_tv_episode_title(parsed, tv_db)
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

            # Record in DB
            downloaded_file = DownloadedFile(
                torrent_id=torrent_db.id,
                filename=media_file.filename,
                final_path=str(media_file.absolute_path),
            )
            db.add(downloaded_file)

        # 5. Cleanup
        # Only cleanup if it was a directory (data_root is non-empty)
        local_download_path = local_torrent_base
        if torrent_info.data_root:
            local_download_path = local_torrent_base / torrent_info.data_root
            cleanup_directory(local_download_path)

        # 6. Finalize DB
        torrent_db.status = DownloadStatus.COMPLETED
        torrent_db.completed_at = datetime.now(UTC).replace(tzinfo=None)
        torrent_db.progress = 1.0
        torrent_db.save_path = str(local_download_path)
        await db.commit()

        # Clean up Redis cache for this torrent
        await typing.cast(
            typing.Awaitable[int], redis_client.delete(f"torrent:{torrent_db.id}")
        )

    except Exception as e:
        torrent_db.status = DownloadStatus.FAILED
        torrent_db.error = str(e)
        await db.commit()

        # Update Redis so the frontend is notified of the error
        await typing.cast(
            typing.Awaitable[int],
            redis_client.hset(
                f"torrent:{torrent_db.id}",
                mapping={
                    "state": "error",
                    "message": str(e),
                    "progress": str(torrent_db.progress),
                },
            ),
        )
        # Set expiry so it doesn't stay forever but long enough for user to see
        await typing.cast(
            typing.Awaitable[bool],
            redis_client.expire(f"torrent:{torrent_db.id}", 3600),
        )
        raise
