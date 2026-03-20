#!/usr/bin/env python3
from __future__ import annotations

import os
import typing
from argparse import ArgumentParser
from time import sleep

import tvdbsimple as tvdb
import yaml

# from process import process
from celery import Celery
from flask import Flask, render_template, request
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb

from .filemanagement import Media, MediaInit

config: dict[str, typing.Any] = {}

app = Flask(__name__)

celery = Celery(app.name)
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

    app.config["CELERY_BROKER_URL"] = config["celery"]["celery_url"]
    app.config["CELERY_RESULT_BACKEND"] = config["celery"]["celery_result"]
    celery.conf.update(app.config)


@celery.task
def process(
    magnet_uri: str, typ: str, app_config: dict[str, typing.Any] | None = None
) -> bool:
    if app_config is None:
        app_config = config

    client = app_config["qbittorrent"]
    tmdb = app_config["tmdb"]
    tvdb = app_config["tvdb"]

    d = app_config["directories"]

    res = client.torrents_add(
        urls=[magnet_uri],
        save_path=os.path.join(d["remote"], d["download"]),
        is_paused=True,
    )

    if res != "Ok.":
        print(f"Torrent add failed: {res}")

    torrent_list = client.torrents_info(status_filter="paused")

    active_torrents = {}

    torrent = None

    for torrent in torrent_list:
        if torrent["magnet_uri"] not in active_torrents:
            obj = {
                "name": torrent["name"],
                "magnet_uri": torrent["magnet_uri"],
                "hash": torrent["hash"],
            }
            client.torrents_resume(obj["hash"])
            active_torrents[obj["magnet_uri"]] = obj
            if torrent["magnet_uri"] == magnet_uri:
                torrent = obj

    print("Torrent in progress")
    while client.torrents_info(hash=torrent["hash"])[0]["state"] != "uploading":
        sleep(1)

    # this assumes that the 0th file is in the root directory of the download
    torrent["data_root"] = os.path.split(
        client.torrents_files(hash=torrent["hash"])[0]["name"]
    )[0]
    client.torrents_delete(delete_files=False, hashes=torrent["hash"])

    print("Torrent complete")

    # TODO: look for media files inside local dir
    # TODO: move files asynchronously

    media = Media(
        app_config,
        MediaInit(
            name=torrent["name"],
            magnet_uri=torrent["magnet_uri"],
            data_root=torrent["data_root"],
            tmdb=tmdb,
            tvdb=tvdb,
            typ=typ,
        ),
    )

    media.process()

    return True


@app.route("/mediamanager")
def index() -> str:
    return render_template("index.html")


@app.route("/mediamanager/datahandler", methods=["POST"])
def handle_data() -> str | tuple[str, int]:
    magnet_uri = request.form.get("magnet_uri")
    typ = request.form.get("type_selector")

    if magnet_uri is None or typ is None:
        return "Missing request data", 400

    print(f"Received request with magnet: {magnet_uri}")

    process.delay(magnet_uri, typ, config)

    return f"Success! Added magnet link {magnet_uri}"


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("config", help="Path to config YAML file")
    args = parser.parse_args()

    init_services(load_config(args.config))
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
