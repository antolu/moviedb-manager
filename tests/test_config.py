from __future__ import annotations

import pytest

from moviedb_manager.config.settings import Settings


def test_settings_default_values() -> None:
    settings = Settings(_env_file=None)  # Ignore .env for this test
    assert settings.qbittorrent.host == "localhost"
    assert settings.qbittorrent.port == 8080
    assert "mkv" in settings.misc.mediaextensions
    assert "srt" in settings.misc.subtitleextensions


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOVIEDB_APIKEYS__TMDB", "test_tmdb_key")
    monkeypatch.setenv("MOVIEDB_DIRECTORIES__MOVIE", "custom_movies")

    settings = Settings(_env_file=None)
    assert settings.apikeys.tmdb == "test_tmdb_key"
    assert settings.directories.movie == "custom_movies"


def test_settings_nested_delimiter(monkeypatch: pytest.MonkeyPatch) -> None:
    # Testing Pydantic Settings nested delimiter behavior
    monkeypatch.setenv("MOVIEDB_CELERY__CELERY_URL", "redis://test:6379/1")
    settings = Settings(_env_file=None)
    assert settings.celery.celery_url == "redis://test:6379/1"
