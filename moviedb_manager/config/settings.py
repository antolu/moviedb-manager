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


class RedisSettings(pydantic.BaseModel):
    url: str = "redis://localhost:6379/0"


class DatabaseSettings(pydantic.BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "moviedb"
    password: str = "moviedb"
    name: str = "moviedb"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class DirectorySettings(pydantic.BaseModel):
    remote: str = "/downloads"
    download: str = "downloads"
    local: str = "/data"
    movie: str = "movies"
    tv: str = "tv"


class MiscSettings(pydantic.BaseModel):
    mediaextensions: list[str] = ["mkv", "mp4", "avi", "m4v"]
    subtitleextensions: list[str] = ["srt", "sub", "ass"]


class SecuritySettings(pydantic.BaseModel):
    auth_base_url: str = "http://localhost"
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:6001/auth/callback"
    login_url: str = "http://localhost/login"
    cookie_name: str = "access_token"
    request_timeout_seconds: int = 10


class Settings(pydantic_settings.BaseSettings):
    apikeys: APIKeys = pydantic.Field(default_factory=APIKeys)
    qbittorrent: QBittorrentSettings = pydantic.Field(
        default_factory=QBittorrentSettings
    )
    redis: RedisSettings = pydantic.Field(default_factory=RedisSettings)
    database: DatabaseSettings = pydantic.Field(default_factory=DatabaseSettings)
    directories: DirectorySettings = pydantic.Field(default_factory=DirectorySettings)
    misc: MiscSettings = pydantic.Field(default_factory=MiscSettings)
    security: SecuritySettings = pydantic.Field(default_factory=SecuritySettings)

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="MOVIEDB_",
        env_nested_delimiter="_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
