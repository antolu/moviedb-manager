from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

MediaType = Literal["movie", "tv"]


class TorrentInfo(BaseModel):
    name: str
    magnet_uri: str
    hash: str
    data_root: str
    files: list[str]


class EpisodeInfo(BaseModel):
    season: int
    episode: int


class MediaFile(BaseModel):
    filename: str
    absolute_path: Path
    media_type: MediaType
    real_name: str | None = None
    episode_info: EpisodeInfo | None = None


class SubtitleFile(BaseModel):
    filename: str
    absolute_path: Path
    real_name: str | None = None
