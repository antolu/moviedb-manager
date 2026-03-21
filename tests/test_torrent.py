from __future__ import annotations

import pathlib
import unittest.mock

import pytest

from moviedb_manager.services.torrent import add_and_wait_for_completion


def test_add_and_wait_for_completion_success() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."

    # Mock return values for torrents_info
    # 1. find added torrent
    # 2. while loop check (exit condition)
    # 3. while loop info (final check)
    mock_client.torrents_info.side_effect = [
        [{"magnet_uri": "mag1", "hash": "h1", "name": "Torrent Name"}],
        [{"state": "uploading", "hash": "h1"}],
    ]

    mock_client.torrents_files.return_value = [{"name": "Torrent Name/file.mkv"}]

    save_path = pathlib.Path("/tmp/downloads")

    # Patch sleep to speed up test
    with unittest.mock.patch(
        "moviedb_manager.services.torrent.time.sleep", return_value=None
    ):
        info = add_and_wait_for_completion(mock_client, "mag1", save_path)

    assert info.hash == "h1"
    assert info.name == "Torrent Name"
    assert info.data_root == "Torrent Name"

    mock_client.torrents_add.assert_called_once()
    mock_client.torrents_resume.assert_called_with("h1")
    mock_client.torrents_delete.assert_called_with(delete_files=False, hashes="h1")


def test_add_and_wait_for_completion_add_failure() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Error: Invalid magnet"

    with pytest.raises(RuntimeError, match="Torrent add failed"):
        add_and_wait_for_completion(mock_client, "mag1", pathlib.Path("/tmp"))


def test_add_and_wait_for_completion_not_found() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."
    mock_client.torrents_info.return_value = []  # No torrents found

    with pytest.raises(RuntimeError, match="Could not find added torrent"):
        add_and_wait_for_completion(mock_client, "mag1", pathlib.Path("/tmp"))


def test_add_and_wait_for_completion_retries_while_downloading() -> None:
    mock_client = unittest.mock.MagicMock()
    mock_client.torrents_add.return_value = "Ok."

    mock_client.torrents_info.side_effect = [
        [{"magnet_uri": "mag1", "hash": "h1", "name": "Torrent Name"}],  # find
        [{"state": "downloading", "hash": "h1"}],  # retry 1
        [{"state": "downloading", "hash": "h1"}],  # retry 2
        [{"state": "completed", "hash": "h1"}],  # finish
    ]

    mock_client.torrents_files.return_value = [{"name": "file.mkv"}]

    with unittest.mock.patch(
        "moviedb_manager.services.torrent.time.sleep", return_value=None
    ):
        info = add_and_wait_for_completion(mock_client, "mag1", pathlib.Path("/tmp"))

    assert not info.data_root  # os.path.split("file.mkv")[0]
    assert mock_client.torrents_info.call_count == 4
