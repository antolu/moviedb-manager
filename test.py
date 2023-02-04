from argparse import ArgumentParser
import re
import errno
import os
import shutil
from time import sleep
from glob import glob, escape

import yaml
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb
import tvdbsimple as tvdb

from filemanagement import Media


parser = ArgumentParser()

parser.add_argument("magnet_link", help="Magnet link")

typ = parser.add_mutually_exclusive_group(required=True)
typ.add_argument("--movie", action="store_true", help="If it's a movie")
typ.add_argument("--tv", action="store_true", help="If it's a TV-series")

parser.add_argument("--multiple-seasons", dest="m_seasons",
                    action="store_true", help="If TV series has multiple nested seasons")
parser.add_argument("--config", required=True, help="Path to config YAML file")

args = parser.parse_args()

if args.movie:
    typ = 'movie'
elif args.tv:
    typ = 'tv'
else:
    raise ValueError('Type not supported')

with open(args.config, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

tmdb = TMDb()
tmdb.api_key = config['apikeys']['tmdb']
movie = Movie()
tvdb.KEYS.API_KEY = config['apikeys']['tvdb']

q = config["qbittorrent"]
d = config["directories"]

client = Client(host=q["host"] + ":" + str(q["port"]),
                username=q["user"], password=q["password"])

print("qBittorrent Version: %s" % client.app_version())

res = client.torrents_add(
    urls=[args.magnet_link], save_path=os.path.join(d['remote'], d["download"]), is_paused=True)

if res != "Ok.":
    print("Torrent add failed: {}".format(res))

torrent_list = client.torrents_info(status_filter='paused')

active_torrents = {}
obj = None

current_torrent = None

for torrent in torrent_list:
    if torrent["state"] == "pausedDL":
        obj = {
            'name': torrent['name'], 
            'magnet_uri': torrent['magnet_uri'], 
            'hash': torrent['hash']
            }
        client.torrents_resume(obj['hash'])
        active_torrents[obj['magnet_uri']] = obj
        current_torrent = obj

print("Torrent in progress")
sleep(1)
while client.torrents_info(hash=current_torrent["hash"])[0]["state"] != "uploading":
    sleep(1)

# this assumes that the 0th file is in the root directory of the download
torrent['data_root'] = os.path.split(client.torrents_files(hash=torrent['hash'])[0]["name"])[0]
client.torrents_delete(delete_files=False, hashes=torrent['hash'])

print("Torrent complete")

# TODO: look for media files inside local dir
# TODO: move files asynchronously

# obj = MediaObject({'name': args.magnet_link, 'hash': 0, 'magnet_uri': ''})

media = Media(config, torrent["name"], torrent["magnet_uri"], torrent["data_root"], movie, tvdb, typ=typ)

media.process()
