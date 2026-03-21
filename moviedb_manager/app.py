from __future__ import annotations

import collections.abc
import contextlib
import os
import typing

import celery
import fastapi
import fastapi.responses
import fastapi.templating
import qbittorrentapi
import uvicorn

from .api.tmdb import TmdbMovieAdapter
from .api.tvdb import TvDbAdapter
from .config.settings import Settings, settings
from .models.media import MediaType
from .services.pipeline import process_torrent_pipeline

# Setup Celery
celery_app = celery.Celery(
    "moviedb-manager",
    broker=settings.celery.celery_url,
    backend=settings.celery.celery_result,
)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:  # noqa: RUF029
    # Initialize API clients
    app.state.movie_db = TmdbMovieAdapter(settings.apikeys.tmdb)
    app.state.tv_db = TvDbAdapter(settings.apikeys.tvdb)

    q = settings.qbittorrent
    app.state.qbt_client = qbittorrentapi.Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    print(f"Using qBittorrent Version: {app.state.qbt_client.app_version()}")
    yield


app = fastapi.FastAPI(lifespan=lifespan)

# Setup templates
templates = fastapi.templating.Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@celery_app.task
def process_task(
    magnet_uri: str, typ: str, settings_dict: dict[str, typing.Any]
) -> bool:
    # Reconstruct settings and clients for the worker
    worker_settings = Settings.model_validate(settings_dict)

    movie_db = TmdbMovieAdapter(worker_settings.apikeys.tmdb)
    tv_db = TvDbAdapter(worker_settings.apikeys.tvdb)

    q = worker_settings.qbittorrent
    qbt_client = qbittorrentapi.Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    process_torrent_pipeline(
        magnet_uri=magnet_uri,
        media_type=typing.cast(MediaType, typ),
        qbt_client=qbt_client,
        movie_db=movie_db,
        tv_db=tv_db,
        settings=worker_settings,
    )

    return True


@app.get("/mediamanager", response_class=fastapi.responses.HTMLResponse)
async def index(request: fastapi.Request) -> fastapi.responses.HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/mediamanager/datahandler")
async def handle_data(
    magnet_uri: str = fastapi.Form(...), type_selector: str = fastapi.Form(...)
) -> str:
    print(f"Received request with magnet: {magnet_uri}")
    process_task.delay(magnet_uri, type_selector, settings.model_dump())
    return f"Success! Added magnet link {magnet_uri}"


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
