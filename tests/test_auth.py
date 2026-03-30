from __future__ import annotations

import unittest.mock

import pytest
from httpx import ASGITransport, AsyncClient

from moviedb_manager.app import app


@pytest.mark.asyncio
async def test_auth_exchange_sets_cookie() -> None:
    mock_response = unittest.mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "broker-token",
        "expires_in": 3600,
    }

    mock_client = unittest.mock.AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

    with unittest.mock.patch(
        "moviedb_manager.app.httpx.AsyncClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/auth/exchange", json={"code": "auth-code"}
            )

    assert response.status_code == 200
    assert response.cookies.get("access_token") == "broker-token"


@pytest.mark.no_auth_override
@pytest.mark.asyncio
async def test_auth_me_validates_token_locally() -> None:
    with (
        unittest.mock.patch(
            "moviedb_manager.app.settings.security.enabled",
            new=True,
        ),
        unittest.mock.patch(
            "moviedb_manager.app._validate_token",
            new=unittest.mock.AsyncMock(
                return_value={"sub": "user-1", "email": "user@example.com"}
            ),
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"access_token": "some-jwt"},
        ) as client:
            response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["sub"] == "user-1"


@pytest.mark.no_auth_override
@pytest.mark.asyncio
async def test_auth_me_returns_401_without_token() -> None:
    with unittest.mock.patch(
        "moviedb_manager.app.settings.security.enabled",
        new=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_refresh_updates_cookie() -> None:
    mock_response = unittest.mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new-access-token",
        "expires_in": 900,
    }
    mock_response.cookies = {}

    mock_client = unittest.mock.AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

    with unittest.mock.patch(
        "moviedb_manager.app.httpx.AsyncClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"refresh_token": "old-refresh-token"},
        ) as client:
            response = await client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert response.cookies.get("access_token") == "new-access-token"


@pytest.mark.asyncio
async def test_auth_refresh_returns_401_without_cookie() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/auth/refresh")

    assert response.status_code == 401
