from __future__ import annotations

import pathlib
import unittest.mock

import pytest

from moviedb_manager.services.torrent import add_and_wait_for_completion


@pytest.mark.asyncio
async def test_add_and_wait_for_completion_success() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."

    # Mock return values for torrents_info
    mock_client.torrents_info.side_effect = [
        [
            {
                "magnet_uri": "magnet:?xt=urn:btih:mag1",
                "hash": "mag1",
                "name": "Torrent Name",
            }
        ],
        [{"state": "uploading", "hash": "mag1", "name": "Torrent Name"}],
    ]

    mock_client.torrents_files.return_value = [{"name": "Torrent Name/file.mkv"}]

    save_path = pathlib.Path("/tmp/downloads")

    # Patch sleep to speed up test
    with unittest.mock.patch(
        "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
    ):
        info = await add_and_wait_for_completion(
            mock_client, "magnet:?xt=urn:btih:mag1", save_path
        )

    assert info.hash == "mag1"
    assert info.name == "Torrent Name"
    assert info.data_root == "Torrent Name"

    # Verify blocking calls were offloaded
    mock_client.torrents_add.assert_called_once()
    mock_client.torrents_resume.assert_called_with(hashes="mag1")
    mock_client.torrents_files.assert_called_with(torrent_hash="mag1")
    mock_client.torrents_delete.assert_called_with(delete_files=False, hashes="mag1")


@pytest.mark.asyncio
async def test_add_and_wait_for_completion_add_failure() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Error: Invalid magnet"

    with pytest.raises(RuntimeError, match="Torrent add failed"):
        await add_and_wait_for_completion(
            mock_client, "magnet:?xt=urn:btih:mag1", pathlib.Path("/tmp")
        )


@pytest.mark.asyncio
async def test_add_and_wait_for_completion_not_found() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."
    mock_client.torrents_info.return_value = []  # No torrents found

    with pytest.raises(RuntimeError, match="Torrent disappeared from qBittorrent"):
        await add_and_wait_for_completion(
            mock_client, "magnet:?xt=urn:btih:mag1", pathlib.Path("/tmp")
        )


@pytest.mark.asyncio
async def test_add_and_wait_for_completion_retries_while_downloading() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."

    mock_client.torrents_info.side_effect = [
        [
            {
                "magnet_uri": "magnet:?xt=urn:btih:mag1",
                "hash": "mag1",
                "name": "Torrent Name",
            }
        ],  # find
        [
            {
                "state": "downloading",
                "hash": "mag1",
                "progress": 0.5,
                "eta": 10,
                "name": "Torrent Name",
            }
        ],  # retry 1
        [
            {
                "state": "downloading",
                "hash": "mag1",
                "progress": 0.9,
                "eta": 2,
                "name": "Torrent Name",
            }
        ],  # retry 2
        [
            {
                "state": "completed",
                "hash": "mag1",
                "progress": 1.0,
                "eta": 0,
                "name": "Torrent Name",
            }
        ],  # finish
    ]

    mock_client.torrents_files.return_value = [{"name": "file.mkv"}]
    mock_redis = unittest.mock.AsyncMock()

    with unittest.mock.patch(
        "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
    ):
        info = await add_and_wait_for_completion(
            mock_client,
            "magnet:?xt=urn:btih:mag1",
            pathlib.Path("/tmp"),
            torrent_id=1,
            redis_client=mock_redis,
        )

    assert not info.data_root  # os.path.split("file.mkv")[0]
    assert mock_client.torrents_info.call_count == 4
    # Verify Redis status update was called
    assert mock_redis.hset.called
    assert mock_redis.expire.called


@pytest.mark.asyncio
async def test_add_and_wait_for_completion_empty_info_loop() -> None:
    # Coverage for line 60: if not info_list: break
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."
    mock_client.torrents_info.side_effect = [
        [
            {
                "magnet_uri": "magnet:?xt=urn:btih:mag1",
                "hash": "mag1",
                "name": "Torrent Name",
            }
        ],  # find
        [],  # vanish from qbt
    ]
    mock_client.torrents_files.return_value = [{"name": "file.mkv"}]

    with (
        unittest.mock.patch(
            "moviedb_manager.services.torrent.asyncio.sleep", return_value=None
        ),
        pytest.raises(RuntimeError, match="Torrent disappeared from qBittorrent"),
    ):
        await add_and_wait_for_completion(
            mock_client, "magnet:?xt=urn:btih:mag1", pathlib.Path("/tmp")
        )
