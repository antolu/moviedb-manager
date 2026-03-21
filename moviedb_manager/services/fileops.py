from __future__ import annotations

import glob
import os
import pathlib
import shutil
import typing

from ..models.media import MediaFile, MediaType, SubtitleFile

if typing.TYPE_CHECKING:
    pass


def find_media_files(
    data_path: pathlib.Path,
    media_extensions: list[str],
    media_type: MediaType = "movie",
) -> list[MediaFile]:
    files: list[MediaFile] = []

    if not data_path.exists():
        return files

    if data_path.is_file():
        if data_path.suffix.lstrip(".") in media_extensions:
            return [
                MediaFile(
                    filename=data_path.name,
                    absolute_path=data_path,
                    media_type=media_type,
                )
            ]
        return files

    for ext in media_extensions:
        found = glob.glob(os.path.join(glob.escape(str(data_path)), "*." + ext))
        for path_str in found:
            path = pathlib.Path(path_str)
            files.append(
                MediaFile(filename=path.name, absolute_path=path, media_type=media_type)
            )

    for item in data_path.iterdir():
        if item.is_dir():
            files.extend(find_media_files(item, media_extensions, media_type))

    return files


def rename_file(
    file: MediaFile | SubtitleFile,
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
    file: MediaFile | SubtitleFile,
    dest_dir: pathlib.Path,
) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_path = dest_dir / file.filename

    file.absolute_path.rename(new_path)
    file.absolute_path = new_path


def cleanup_directory(path: pathlib.Path) -> None:
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
