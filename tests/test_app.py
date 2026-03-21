from unittest.mock import patch

from fastapi.testclient import TestClient

from moviedb_manager.app import app

client = TestClient(app)


def test_root_endpoint() -> None:
    # Smoke test for the main index page
    response = client.get("/mediamanager")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_handle_data_success() -> None:
    # Mock the celery task's delay method
    with patch("moviedb_manager.app.process_task.delay") as mock_delay:
        response = client.post(
            "/mediamanager/datahandler",
            data={"magnet_uri": "mag1", "type_selector": "movie"},
        )
        assert response.status_code == 200
        assert "Success! Added magnet link" in response.text
        mock_delay.assert_called_once()
        # Verify it passed the magnet, type and dumped settings
        args = mock_delay.call_args[0]
        assert args[0] == "mag1"
        assert args[1] == "movie"
        assert isinstance(args[2], dict)


def test_handle_data_missing_form_data() -> None:
    response = client.post("/mediamanager/datahandler", data={"magnet_uri": "mag1"})
    # FastAPI returns 422 Unprocessable Entity for missing required form fields
    assert response.status_code == 422


def test_lifespan_initialization() -> None:
    # Test that lifespan sets up the state
    # Since we can't easily trigger lifespan in TestClient for all tests,
    # we can at least check if the logic in lifespan is correct by calling it or mocking it.
    with (
        patch("moviedb_manager.app.Client"),
        patch("moviedb_manager.api.tmdb.TmdbMovieAdapter"),
        patch("moviedb_manager.api.tvdb.TvDbAdapter"),
        client,
    ):
        assert hasattr(app.state, "movie_db")
        assert hasattr(app.state, "tv_db")
        assert hasattr(app.state, "qbt_client")
