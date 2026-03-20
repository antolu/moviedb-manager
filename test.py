import os
import typing
from argparse import ArgumentParser
from time import sleep

import tvdbsimple as tvdb
import yaml
from filemanagement import Media, MediaInit
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb

parser = ArgumentParser()

parser.add_argument("magnet_link", help="Magnet link")

typ = parser.add_mutually_exclusive_group(required=True)
typ.add_argument("--movie", action="store_true", help="If it's a movie")
typ.add_argument("--tv", action="store_true", help="If it's a TV-series")

parser.add_argument(
    "--multiple-seasons",
    dest="m_seasons",
    action="store_true",
    help="If TV series has multiple nested seasons",
)
parser.add_argument("--config", required=True, help="Path to config YAML file")

args = parser.parse_args()

if args.movie:
    media_type = "movie"
elif args.tv:
    media_type = "tv"
else:
    msg = "Type not supported"
    raise ValueError(msg)

with open(args.config, encoding="utf-8") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

tmdb = TMDb()
tmdb.api_key = config["apikeys"]["tmdb"]
movie = Movie()
tvdb.KEYS.API_KEY = config["apikeys"]["tvdb"]

q = config["qbittorrent"]
d = config["directories"]

client = Client(
    host=q["host"] + ":" + str(q["port"]), username=q["user"], password=q["password"]
)

print(f"qBittorrent Version: {client.app_version()}")

res = client.torrents_add(
    urls=[args.magnet_link],
    save_path=os.path.join(d["remote"], d["download"]),
    is_paused=True,
)

if res != "Ok.":
    print(f"Torrent add failed: {res}")

torrent_list = client.torrents_info(status_filter="paused")

active_torrents: dict[str, dict[str, typing.Any]] = {}
obj: dict[str, typing.Any] | None = None

torrent: dict[str, typing.Any] | None = None

for torrent in torrent_list:
    torrent_magnet = typing.cast(str, torrent["magnet_uri"])
    if torrent_magnet not in active_torrents:
        obj = {
            "name": typing.cast(str, torrent["name"]),
            "magnet_uri": torrent_magnet,
            "hash": typing.cast(str, torrent["hash"]),
        }
        client.torrents_resume(obj["hash"])
        active_torrents[torrent_magnet] = obj
        if torrent_magnet == args.magnet_link:
            torrent = obj

if torrent is None:
    msg = "Torrent not found"
    raise ValueError(msg)

print("Torrent in progress")
while client.torrents_info(hash=torrent["hash"])[0]["state"] != "uploading":
    sleep(1)

# this assumes that the 0th file is in the root directory of the download
file_name = typing.cast(str, client.torrents_files(hash=torrent["hash"])[0]["name"])
torrent["data_root"] = os.path.split(file_name)[0]
client.torrents_delete(delete_files=False, hashes=torrent["hash"])

print("Torrent complete")

# TODO: look for media files inside local dir
# TODO: move files asynchronously

# obj = MediaObject({'name': args.magnet_link, 'hash': 0, 'magnet_uri': ''})

media = Media(
    config,
    MediaInit(
        name=typing.cast(str, torrent["name"]),
        magnet_uri=typing.cast(str, torrent["magnet_uri"]),
        data_root=typing.cast(str, torrent["data_root"]),
        tmdb=movie,
        tvdb=tvdb,
        typ=media_type,
    ),
)

media.process()
