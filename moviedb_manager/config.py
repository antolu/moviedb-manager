from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIKeys(BaseModel):
    tmdb: str = ""
    tvdb: str = ""


class QBittorrentSettings(BaseModel):
    host: str = "localhost"
    port: int = 8080
    user: str = "admin"
    password: str = "adminadmin"


class CelerySettings(BaseModel):
    celery_url: str = "redis://localhost:6379/0"
    celery_result: str = "redis://localhost:6379/0"


class DirectorySettings(BaseModel):
    remote: str = "/downloads"
    download: str = "downloads"
    local: str = "/data"
    movie: str = "movies"
    tv: str = "tv"


class MiscSettings(BaseModel):
    mediaextensions: list[str] = ["mkv", "mp4", "avi", "m4v"]
    subtitleextensions: list[str] = ["srt", "sub", "ass"]


class Settings(BaseSettings):
    apikeys: APIKeys = Field(default_factory=APIKeys)
    qbittorrent: QBittorrentSettings = Field(default_factory=QBittorrentSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    misc: MiscSettings = Field(default_factory=MiscSettings)

    model_config = SettingsConfigDict(
        env_prefix="MOVIEDB_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
