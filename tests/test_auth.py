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


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_auth_me_uses_broker_validation() -> None:
    with unittest.mock.patch(
        "moviedb_manager.app._fetch_current_user_from_broker",
        new=unittest.mock.AsyncMock(
            return_value={"id": "user-1", "email": "user@example.com"}
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"access_token": "broker-token"},
        ) as client:
            response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == "user-1"
