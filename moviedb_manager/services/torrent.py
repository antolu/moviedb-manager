from __future__ import annotations

import os
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

from moviedb_manager.models.media import TorrentInfo

if TYPE_CHECKING:
    from qbittorrentapi import Client


def add_and_wait_for_completion(
    client: Client, magnet_uri: str, save_path: Path
) -> TorrentInfo:
    res = client.torrents_add(
        urls=[magnet_uri],
        save_path=str(save_path),
        is_paused=True,
    )

    if res != "Ok.":
        msg = f"Torrent add failed: {res}"
        raise RuntimeError(msg)

    # Find the added torrent
    torrent_list = client.torrents_info(status_filter="paused")
    target_torrent = None
    for t in torrent_list:
        if t["magnet_uri"] == magnet_uri:
            client.torrents_resume(str(t["hash"]))
            target_torrent = t
            break

    if not target_torrent:
        msg = "Could not find added torrent"
        raise RuntimeError(msg)

    torrent_hash = str(target_torrent["hash"])

    # Wait for completion (state becomes 'uploading' or similar)
    while True:
        info = client.torrents_info(hashes=torrent_hash)[0]
        if info["state"] in {"uploading", "stalledUP", "completed"}:
            break
        sleep(1)

    # Get data root (directory or file name)
    files = client.torrents_files(hashes=torrent_hash)
    data_root = os.path.split(str(files[0]["name"]))[0]

    # Clean up from qBittorrent but keep files
    client.torrents_delete(delete_files=False, hashes=torrent_hash)

    return TorrentInfo(
        name=str(target_torrent["name"]),
        magnet_uri=magnet_uri,
        hash=torrent_hash,
        data_root=data_root,
    )
