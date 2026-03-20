from __future__ import annotations

import os
from time import sleep

import tvdbsimple as tvdb
import uvicorn
from celery import Celery
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb

from .config import settings
from .filemanagement import Media, MediaInit

app = FastAPI()

# Setup templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

celery = Celery(
    "moviedb-manager",
    broker=settings.celery.celery_url,
    backend=settings.celery.celery_result,
)
tmdb = TMDb()
movie = Movie()


def init_services() -> None:
    tmdb.api_key = settings.apikeys.tmdb
    tvdb.KEYS.API_KEY = settings.apikeys.tvdb

    q = settings.qbittorrent
    client = Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )

    print(f"Using qBittorrent Version: {client.app_version()}")

    # we store the client in a global or similar if needed, but here it was in 'config'
    # based on the original code, 'config' was used as a service locator
    # let's keep a global variable for the client if needed, or just re-init as needed.
    # actually, the original code used 'config' to pass around.
    # let's keep a simple dict for services if needed, or better, use dependency injection or globals.
    settings.model_extra = {"qbittorrent_client": client}


@celery.task
def process(magnet_uri: str, typ: str) -> bool:
    q = settings.qbittorrent
    client = Client(
        host=f"{q.host}:{q.port}",
        username=q.user,
        password=q.password,
    )
    d = settings.directories

    res = client.torrents_add(
        urls=[magnet_uri],
        save_path=os.path.join(d.remote, d.download),
        is_paused=True,
    )

    if res != "Ok.":
        print(f"Torrent add failed: {res}")

    torrent_list = client.torrents_info(status_filter="paused")
    torrent = None

    for t in torrent_list:
        if t["magnet_uri"] == magnet_uri:
            client.torrents_resume(t["hash"])
            torrent = {
                "name": t["name"],
                "magnet_uri": t["magnet_uri"],
                "hash": t["hash"],
            }
            break

    if not torrent:
        print("Could not find added torrent")
        return False

    print("Torrent in progress")
    while client.torrents_info(hash=torrent["hash"])[0]["state"] != "uploading":
        sleep(1)

    # this assumes that the 0th file is in the root directory of the download
    torrent["data_root"] = os.path.split(
        client.torrents_files(hash=torrent["hash"])[0]["name"]
    )[0]
    client.torrents_delete(delete_files=False, hashes=torrent["hash"])

    print("Torrent complete")

    media = Media(
        settings,
        MediaInit(
            name=torrent["name"],
            magnet_uri=torrent["magnet_uri"],
            data_root=torrent["data_root"],
            tmdb=movie,
            tvdb=tvdb,
            typ=typ,
        ),
    )

    media.process()

    return True


@app.get("/mediamanager", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/mediamanager/datahandler")
async def handle_data(
    magnet_uri: str = Form(...), type_selector: str = Form(...)
) -> str:
    print(f"Received request with magnet: {magnet_uri}")
    process.delay(magnet_uri, type_selector)
    return f"Success! Added magnet link {magnet_uri}"


def main() -> None:
    init_services()
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
