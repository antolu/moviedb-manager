from __future__ import annotations

import pathlib

import pytest

from moviedb_manager.models.media import MediaFile, SubtitleFile
from moviedb_manager.services.fileops import (
    cleanup_directory,
    find_media_files,
    move_file,
    rename_file,
)


def test_find_media_files_directory(media_root: pathlib.Path) -> None:
    files = find_media_files(media_root / "downloads", ["mkv", "mp4"])
    filenames = {f.filename for f in files}
    assert "Movie.2023.1080p.mkv" in filenames
    assert "file.mp4" in filenames
    assert len(files) == 2


def test_find_media_files_single_file(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "movie.mkv"
    f.touch()
    files = find_media_files(f, ["mkv", "mp4"])
    assert len(files) == 1
    assert files[0].filename == "movie.mkv"


def test_find_media_files_single_file_wrong_extension(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "movie.txt"
    f.touch()
    files = find_media_files(f, ["mkv", "mp4"])
    assert files == []


def test_find_media_files_nonexistent_path(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "doesnotexist"
    files = find_media_files(missing, ["mkv"])
    assert files == []


def test_find_media_files_nested(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "deep.mkv").touch()
    (tmp_path / "top.mp4").touch()

    files = find_media_files(tmp_path, ["mkv", "mp4"])
    filenames = {f.filename for f in files}
    assert "deep.mkv" in filenames
    assert "top.mp4" in filenames


def test_find_media_files_ignores_non_media(tmp_path: pathlib.Path) -> None:
    (tmp_path / "movie.mkv").touch()
    (tmp_path / "movie.nfo").touch()
    (tmp_path / "cover.jpg").touch()

    files = find_media_files(tmp_path, ["mkv"])
    assert len(files) == 1
    assert files[0].filename == "movie.mkv"


def test_find_media_files_media_type_propagated(tmp_path: pathlib.Path) -> None:
    (tmp_path / "ep.mkv").touch()
    files = find_media_files(tmp_path, ["mkv"], media_type="tv")
    assert files[0].media_type == "tv"


def test_rename_file_mediafile(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "old_name.mkv"
    src.touch()
    media_file = MediaFile(
        filename="old_name.mkv", absolute_path=src, media_type="movie"
    )

    rename_file(media_file, "New Name (2023)")

    assert media_file.filename == "New Name (2023).mkv"
    assert media_file.real_name == "New Name (2023)"
    assert not src.exists()
    assert (tmp_path / "New Name (2023).mkv").exists()


def test_rename_file_subtitle(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "subtitle.srt"
    src.touch()
    sub = SubtitleFile(filename="subtitle.srt", absolute_path=src)

    rename_file(sub, "Movie Title (2023)")

    assert sub.filename == "Movie Title (2023).srt"
    assert (tmp_path / "Movie Title (2023).srt").exists()


def test_move_file_creates_dest_dir(tmp_path: pathlib.Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dest_dir = tmp_path / "new" / "nested" / "dir"

    f = src_dir / "file.mkv"
    f.touch()
    media_file = MediaFile(filename="file.mkv", absolute_path=f, media_type="movie")

    move_file(media_file, dest_dir)

    assert dest_dir.exists()
    assert (dest_dir / "file.mkv").exists()
    assert not f.exists()
    assert media_file.absolute_path == dest_dir / "file.mkv"


def test_cleanup_directory(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "to_delete"
    target.mkdir()
    (target / "junk.txt").touch()

    cleanup_directory(target)
    assert not target.exists()


def test_cleanup_directory_nonexistent(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "ghost"
    cleanup_directory(missing)  # should not raise


@pytest.mark.parametrize("ext", ["mkv", "mp4", "avi", "m4v"])
def test_find_media_files_all_supported_extensions(
    tmp_path: pathlib.Path, ext: str
) -> None:
    (tmp_path / f"video.{ext}").touch()
    files = find_media_files(tmp_path, ["mkv", "mp4", "avi", "m4v"])
    assert len(files) == 1
