#!/usr/bin/env python3
from __future__ import annotations

import os
import typing
from argparse import ArgumentParser
from time import sleep

import tvdbsimple as tvdb
import uvicorn
import yaml
from celery import Celery
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb

from .filemanagement import Media, MediaInit

config: dict[str, typing.Any] = {}

app = FastAPI()

# Setup templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

celery = Celery("moviedb-manager")
tmdb = TMDb()
movie = Movie()


def load_config(config_path: str) -> dict[str, typing.Any]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def init_services(app_config: dict[str, typing.Any]) -> None:
    config.clear()
    config.update(app_config)

    tmdb.api_key = config["apikeys"]["tmdb"]
    tvdb.KEYS.API_KEY = config["apikeys"]["tvdb"]

    q = config["qbittorrent"]
    client = Client(
        host=q["host"] + ":" + str(q["port"]),
        username=q["user"],
        password=q["password"],
    )

    print(f"Using qBittorrent Version: {client.app_version()}")

    config["qbittorrent"] = client
    config["tmdb"] = movie
    config["tvdb"] = tvdb

    # Celery config
    celery.conf.update(
        broker_url=config["celery"]["celery_url"],
        result_backend=config["celery"]["celery_result"],
    )


@celery.task
def process(
    magnet_uri: str, typ: str, app_config: dict[str, typing.Any] | None = None
) -> bool:
    if app_config is None:
        app_config = config

    client = app_config["qbittorrent"]
    tmdb_svc = app_config["tmdb"]
    tvdb_svc = app_config["tvdb"]
    d = app_config["directories"]

    res = client.torrents_add(
        urls=[magnet_uri],
        save_path=os.path.join(d["remote"], d["download"]),
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
        app_config,
        MediaInit(
            name=torrent["name"],
            magnet_uri=torrent["magnet_uri"],
            data_root=torrent["data_root"],
            tmdb=tmdb_svc,
            tvdb=tvdb_svc,
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
    process.delay(magnet_uri, type_selector, config)
    return f"Success! Added magnet link {magnet_uri}"


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("config", help="Path to config YAML file")
    args = parser.parse_args()

    init_services(load_config(args.config))
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
