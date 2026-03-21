from __future__ import annotations

import pydantic
import pydantic_settings


class APIKeys(pydantic.BaseModel):
    tmdb: str = ""
    tvdb: str = ""


class QBittorrentSettings(pydantic.BaseModel):
    host: str = "localhost"
    port: int = 8080
    user: str = "admin"
    password: str = "adminadmin"


class CelerySettings(pydantic.BaseModel):
    celery_url: str = "redis://localhost:6379/0"
    celery_result: str = "redis://localhost:6379/0"


class DirectorySettings(pydantic.BaseModel):
    remote: str = "/downloads"
    download: str = "downloads"
    local: str = "/data"
    movie: str = "movies"
    tv: str = "tv"


class MiscSettings(pydantic.BaseModel):
    mediaextensions: list[str] = ["mkv", "mp4", "avi", "m4v"]
    subtitleextensions: list[str] = ["srt", "sub", "ass"]


class Settings(pydantic_settings.BaseSettings):
    apikeys: APIKeys = pydantic.Field(default_factory=APIKeys)
    qbittorrent: QBittorrentSettings = pydantic.Field(
        default_factory=QBittorrentSettings
    )
    celery: CelerySettings = pydantic.Field(default_factory=CelerySettings)
    directories: DirectorySettings = pydantic.Field(default_factory=DirectorySettings)
    misc: MiscSettings = pydantic.Field(default_factory=MiscSettings)

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="MOVIEDB_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
