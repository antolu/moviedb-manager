from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import os
import typing
from typing import Annotated

import fastapi
import qbittorrentapi
import redis.asyncio as redis
import uvicorn
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from .api.tmdb import TmdbMovieAdapter
from .api.tvdb import TvDbAdapter
from .config.settings import settings
from .db import AsyncSessionLocal, DownloadedFile, TorrentDownload, get_db
from .models.media import MediaType
from .services.pipeline import process_torrent_pipeline


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
    # Initialize API clients
    app.state.movie_db = TmdbMovieAdapter(settings.apikeys.tmdb)
    app.state.tv_db = TvDbAdapter(settings.apikeys.tvdb)

    # Redis for caching transient torrent status
    app.state.redis = redis.from_url(settings.redis.url)

    q = settings.qbittorrent
    app.state.qbt_client = qbittorrentapi.Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    # Basic check
    try:
        await asyncio.to_thread(app.state.qbt_client.app_version)
    except Exception as e:
        print(f"Warning: Could not connect to qBittorrent: {e}")

    yield

    await app.state.redis.close()


app = fastapi.FastAPI(lifespan=lifespan)


# API Endpoints


@app.get("/api/status")
async def get_api_status() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


async def run_pipeline_task(magnet_uri: str, media_type: str) -> None:
    # Re-create clients inside task for safety, similar to worker
    movie_db = TmdbMovieAdapter(settings.apikeys.tmdb)
    tv_db = TvDbAdapter(settings.apikeys.tvdb)

    q = settings.qbittorrent
    qbt_client = qbittorrentapi.Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    redis_client = redis.from_url(settings.redis.url)

    async with AsyncSessionLocal() as db_session:
        await process_torrent_pipeline(
            magnet_uri=magnet_uri,
            media_type=typing.cast(MediaType, media_type),
            qbt_client=qbt_client,
            movie_db=movie_db,
            tv_db=tv_db,
            settings=settings,
            db=db_session,
            redis_client=redis_client,
        )
    await redis_client.close()


@app.post("/api/torrents")
async def add_torrent(
    db: Annotated[AsyncSession, fastapi.Depends(get_db)],
    background_tasks: fastapi.BackgroundTasks,
    magnet_uri: str = fastapi.Body(..., embed=True),
    media_type: str = fastapi.Body(..., embed=True),
) -> dict[str, str]:
    """Submit a new magnet link for processing."""
    if not magnet_uri.startswith("magnet:?xt=urn:btih:"):
        raise fastapi.HTTPException(status_code=400, detail="Invalid magnet URI")

    background_tasks.add_task(run_pipeline_task, magnet_uri, media_type)
    return {"message": "Torrent added to queue", "magnet_uri": magnet_uri}


@app.get("/api/torrents", response_model=None)
async def list_torrents(
    db: Annotated[AsyncSession, fastapi.Depends(get_db)],
) -> list[TorrentDownload]:
    """List active and recently added torrents."""
    query = select(TorrentDownload).order_by(TorrentDownload.added_at.desc()).limit(20)
    result = await db.execute(query)
    return list(result.scalars().all())


async def event_generator(
    request: fastapi.Request,
    redis_client: redis.Redis,
) -> collections.abc.AsyncGenerator[dict[str, str | list[dict[str, str]]]]:
    try:
        while True:
            if await request.is_disconnected():
                break

            # Find all active torrent keys in Redis
            keys = await typing.cast(
                typing.Awaitable[list[str]], redis_client.keys("torrent:*")
            )
            updates: list[dict[str, str]] = []
            for key in keys:
                data = await typing.cast(
                    typing.Awaitable[dict[str, str]], redis_client.hgetall(key)
                )
                if data:
                    # Decode bytes to strings
                    decoded: dict[str, str] = data.copy()
                    decoded["id"] = key.split(":")[1]
                    updates.append(decoded)

            if updates:
                yield {"data": updates}

            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass


@app.get("/api/torrents/stream")
async def stream_torrents(request: fastapi.Request) -> EventSourceResponse:
    """SSE endpoint for live torrent status updates from Redis."""
    redis_client: redis.Redis = request.app.state.redis
    return EventSourceResponse(event_generator(request, redis_client))


@app.get("/api/history", response_model=None)
async def get_history(
    db: Annotated[AsyncSession, fastapi.Depends(get_db)],
) -> list[DownloadedFile]:
    """Get history of completed downloads."""
    query = select(DownloadedFile).order_by(DownloadedFile.moved_at.desc()).limit(50)
    result = await db.execute(query)
    return list(result.scalars().all())


# Serve Frontend
def configure_frontend(app: fastapi.FastAPI) -> None:
    # Search order: local static/ (Docker build), then frontend/dist (Local dev build)
    app_dir = os.path.dirname(__file__)
    static_dir = os.path.join(app_dir, "static")
    frontend_dist = os.path.abspath(os.path.join(app_dir, "..", "frontend", "dist"))

    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    elif os.path.exists(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


configure_frontend(app)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
