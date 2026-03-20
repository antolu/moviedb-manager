from __future__ import annotations

from pathlib import Path

from moviedb_manager.models.media import MediaFile
from moviedb_manager.services.fileops import find_media_files, move_file, rename_file


def test_find_media_files(media_root: Path) -> None:
    extensions = ["mkv", "mp4"]
    files = find_media_files(media_root / "downloads", extensions)

    filenames = {f.filename for f in files}
    assert "Movie.2023.1080p.mkv" in filenames
    assert "file.mp4" in filenames
    assert len(files) == 2  # noqa: PLR2004


def test_rename_file(tmp_path: Path) -> None:
    file_path = tmp_path / "old_name.mkv"
    file_path.touch()

    media_file = MediaFile(
        filename="old_name.mkv",
        absolute_path=file_path,
        media_type="movie",
    )

    rename_file(media_file, "New Name (2023)")

    assert media_file.filename == "New Name (2023).mkv"
    assert media_file.real_name == "New Name (2023)"
    assert not file_path.exists()
    assert (tmp_path / "New Name (2023).mkv").exists()


def test_move_file(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dest_dir = tmp_path / "dest"

    file_path = src_dir / "file.mkv"
    file_path.touch()

    media_file = MediaFile(
        filename="file.mkv",
        absolute_path=file_path,
        media_type="movie",
    )

    move_file(media_file, dest_dir)

    assert not file_path.exists()
    assert (dest_dir / "file.mkv").exists()
    assert media_file.absolute_path == dest_dir / "file.mkv"
