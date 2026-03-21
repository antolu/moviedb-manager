from __future__ import annotations

import asyncio
import pathlib
import typing

import qbittorrentapi
import redis.asyncio as redis

from ..models.media import TorrentInfo

if typing.TYPE_CHECKING:
    pass


import re


async def add_and_wait_for_completion(
    client: qbittorrentapi.Client,
    magnet_uri: str,
    save_path: pathlib.Path,
    torrent_id: int | None = None,
    redis_client: redis.Redis | None = None,
) -> TorrentInfo:
    """
    Adds a torrent and waits for it to finish downloading.
    Updates Redis with progress if redis_client and torrent_id are provided.
    """
    # Extract hash from magnet URI
    match = re.search(r"btih:([a-zA-Z0-9]+)", magnet_uri)
    if not match:
        msg = f"Invalid magnet URI: {magnet_uri}"
        raise ValueError(msg)
    torrent_hash = match.group(1).lower()

    # Add the torrent (paused to avoid racing)
    res = await asyncio.to_thread(
        client.torrents_add,
        urls=[magnet_uri],
        save_path=str(save_path),
        is_paused=True,
    )

    if res != "Ok.":
        msg = f"Torrent add failed: {res}"
        raise RuntimeError(msg)

    # Resume the torrent
    await asyncio.to_thread(client.torrents_resume, hashes=torrent_hash)

    # Wait for completion
    # Define states that indicate the download is finished
    COMPLETED_STATES = {
        "uploading",
        "stalledUP",
        "pausedUP",
        "queuedUP",
        "completed",
        "checkingUP",
    }

    while True:
        info_list = await asyncio.to_thread(client.torrents_info, hashes=torrent_hash)
        if not info_list:
            # If it's gone, maybe it was finished and removed?
            # But we are the ones removing it later.
            msg = "Torrent disappeared from qBittorrent"
            raise RuntimeError(msg)

        info = info_list[0]
        progress = typing.cast(float, info.get("progress", 0.0))
        state = typing.cast(str, info.get("state", "unknown"))

        # Update Redis status if possible
        if redis_client and torrent_id:
            status_data = {
                "progress": str(progress),
                "eta": str(info.get("eta", 0)),
                "state": state,
                "name": str(info.get("name", "Unknown")),
            }
            await typing.cast(
                typing.Awaitable[int],
                redis_client.hset(f"torrent:{torrent_id}", mapping=status_data),
            )
            await typing.cast(
                typing.Awaitable[int],
                redis_client.expire(f"torrent:{torrent_id}", 3600),
            )

        # Check if finished
        if progress >= 0.999 or state in COMPLETED_STATES:
            break

        await asyncio.sleep(2)

    # Get files list
    files = await asyncio.to_thread(client.torrents_files, hashes=torrent_hash)
    file_paths = [str(f["name"]) for f in files]

    # Calculate data_root (common directory or empty if single file in root)
    if not file_paths:
        data_root = ""
    else:
        # Check if the first file is in a subdirectory
        first_path = pathlib.Path(file_paths[0])
        data_root = str(first_path.parts[0]) if len(first_path.parts) > 1 else ""

    # Clean up from qBittorrent but keep files
    await asyncio.to_thread(
        client.torrents_delete, delete_files=False, hashes=torrent_hash
    )

    return TorrentInfo(
        name=str(info["name"]),
        magnet_uri=magnet_uri,
        hash=torrent_hash,
        data_root=data_root,
        files=file_paths,
    )
