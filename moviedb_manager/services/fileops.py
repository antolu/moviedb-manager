from __future__ import annotations

import os
import shutil
from glob import escape, glob
from pathlib import Path
from typing import TYPE_CHECKING

import moviedb_manager.models.media

if TYPE_CHECKING:
    pass


def find_media_files(
    data_path: Path,
    media_extensions: list[str],
    media_type: moviedb_manager.models.media.MediaType = "movie",
) -> list[moviedb_manager.models.media.MediaFile]:
    files: list[moviedb_manager.models.media.MediaFile] = []

    if not data_path.exists():
        return files

    if data_path.is_file():
        if data_path.suffix.lstrip(".") in media_extensions:
            return [
                moviedb_manager.models.media.MediaFile(
                    filename=data_path.name,
                    absolute_path=data_path,
                    media_type=media_type,
                )
            ]
        return files

    for ext in media_extensions:
        found = glob(os.path.join(escape(str(data_path)), "*." + ext))
        for path_str in found:
            path = Path(path_str)
            files.append(
                moviedb_manager.models.media.MediaFile(
                    filename=path.name, absolute_path=path, media_type=media_type
                )
            )

    for item in data_path.iterdir():
        if item.is_dir():
            files.extend(find_media_files(item, media_extensions, media_type))

    return files


def rename_file(
    file: moviedb_manager.models.media.MediaFile
    | moviedb_manager.models.media.SubtitleFile,
    new_base_name: str,
) -> None:
    extension = file.absolute_path.suffix
    new_name = new_base_name + extension
    new_path = file.absolute_path.parent / new_name

    file.absolute_path.rename(new_path)
    file.filename = new_name
    file.absolute_path = new_path
    file.real_name = new_base_name


def move_file(
    file: moviedb_manager.models.media.MediaFile
    | moviedb_manager.models.media.SubtitleFile,
    dest_dir: Path,
) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_path = dest_dir / file.filename

    file.absolute_path.rename(new_path)
    file.absolute_path = new_path


def cleanup_directory(path: Path) -> None:
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
