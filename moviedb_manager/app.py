from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

import uvicorn
from celery import Celery
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from qbittorrentapi import Client

import moviedb_manager.api.tmdb
import moviedb_manager.api.tvdb
import moviedb_manager.config.settings
import moviedb_manager.models.media
import moviedb_manager.services.pipeline

# Setup Celery
celery = Celery(
    "moviedb-manager",
    broker=moviedb_manager.config.settings.settings.celery.celery_url,
    backend=moviedb_manager.config.settings.settings.celery.celery_result,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: RUF029
    # Initialize API clients
    app.state.movie_db = moviedb_manager.api.tmdb.TmdbMovieAdapter(
        moviedb_manager.config.settings.settings.apikeys.tmdb
    )
    app.state.tv_db = moviedb_manager.api.tvdb.TvDbAdapter(
        moviedb_manager.config.settings.settings.apikeys.tvdb
    )

    q = moviedb_manager.config.settings.settings.qbittorrent
    app.state.qbt_client = Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    print(f"Using qBittorrent Version: {app.state.qbt_client.app_version()}")
    yield


app = FastAPI(lifespan=lifespan)

# Setup templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@celery.task
def process_task(magnet_uri: str, typ: str, settings_dict: dict[str, Any]) -> bool:
    # Reconstruct settings and clients for the worker
    worker_settings = moviedb_manager.config.settings.Settings.model_validate(
        settings_dict
    )

    movie_db = moviedb_manager.api.tmdb.TmdbMovieAdapter(worker_settings.apikeys.tmdb)
    tv_db = moviedb_manager.api.tvdb.TvDbAdapter(worker_settings.apikeys.tvdb)

    q = worker_settings.qbittorrent
    qbt_client = Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    moviedb_manager.services.pipeline.process_torrent_pipeline(
        magnet_uri=magnet_uri,
        media_type=cast(moviedb_manager.models.media.MediaType, typ),
        qbt_client=qbt_client,
        movie_db=movie_db,
        tv_db=tv_db,
        settings=worker_settings,
    )

    return True


@app.get("/mediamanager", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/mediamanager/datahandler")
async def handle_data(
    magnet_uri: str = Form(...), type_selector: str = Form(...)
) -> str:
    print(f"Received request with magnet: {magnet_uri}")
    process_task.delay(
        magnet_uri, type_selector, moviedb_manager.config.settings.settings.model_dump()
    )
    return f"Success! Added magnet link {magnet_uri}"


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
