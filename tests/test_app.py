from __future__ import annotations

from fastapi.testclient import TestClient

from moviedb_manager.app import app

client = TestClient(app)


def test_root_endpoint() -> None:
    # Basic smoke test for the app
    response = client.get("/mediamanager")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
