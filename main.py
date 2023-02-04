#!/usr/bin/env python3

from argparse import ArgumentParser
import re
import errno
import os
import sys
import shutil
from time import sleep
from glob import glob, escape
from multiprocessing import Process

from flask import Flask, render_template, request
import yaml
from qbittorrentapi import Client
from tmdbv3api import Movie, TMDb
import tvdbsimple as tvdb

from filemanagement import Media
# from process import process

from celery import Celery


parser = ArgumentParser()

parser.add_argument("config", help="Path to config YAML file")

args = parser.parse_args()

global config
with open(args.config, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

tmdb = TMDb()
tmdb.api_key = config['apikeys']['tmdb']
movie = Movie()
tvdb.KEYS.API_KEY = config['apikeys']['tvdb']

q = config["qbittorrent"]
d = config["directories"]

try:
    client = Client(host=q["host"] + ":" + str(q["port"]),
                    username=q["user"], password=q["password"])
except:
    log.error("Could not connect to BitTorrent.")
log.debug("Connected to qBittorrent with version: {}".format(client.app_version()))

config["qbittorrent"] = client
config["tmdb"] = movie
config["tvdb"] = tvdb

log.info("Starting Flask...")
app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = config["celery"]["celery_url"]
app.config['CELERY_RESULT_BACKEND'] = config["celery"]["celery_result"]

log.info("Starting Celery...")
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@celery.task
def process(magnet_uri: str, typ: str, config):
    client = config["qbittorrent"]
    tmdb = config["tmdb"]
    tvdb = config["tvdb"]

    d = config["directories"]

    res= client.torrents_add(
        urls=[magnet_uri], save_path=os.path.join(d['remote'], d["download"]), is_paused=True)

    if res != "Ok.":
        print("Torrent add failed: {}".format(res))

    torrent_list= client.torrents_info(status_filter='paused')

    active_torrents= {}

    current_torrent= None

    for torrent in torrent_list:
        if torrent["magnet_uri"] not in active_torrents:
            obj= {
                'name': torrent['name'],
                'magnet_uri': torrent['magnet_uri'],
                'hash': torrent['hash']
            }
            client.torrents_resume(obj['hash'])
            active_torrents[obj['magnet_uri']]= obj
            current_torrent= obj

    log.debug("Torrent in progress")
    while client.torrents_info(hash=current_torrent["hash"])[0]["state"] != "uploading":
        sleep(1)

    # this assumes that the 0th file is in the root directory of the download
    torrent['data_root']= os.path.split(
        client.torrents_files(hash=torrent['hash'])[0]["name"])[0]
    client.torrents_delete(delete_files=False, hashes=torrent['hash'])

    log.debug("Torrent complete")

    # TODO: look for media files inside local dir
    # TODO: move files asynchronously

    media= Media(config, torrent["name"], torrent["magnet_uri"],
                torrent["data_root"], tmdb, tvdb, typ=typ)

    media.process()

    return True

@app.route("/mediamanager")
def index():
    return render_template("index.html")


@app.route("/mediamanager/datahandler", methods=["POST"])
def handle_data():
    magnet_uri= request.form.get("magnet_uri")
    typ= request.form.get("type_selector")

    log.debug("Received request with magnet: {}".format(magnet_uri))

    task= process(magnet_uri, typ, config).delay()

    return "Success! Added magnet link {}".format(magnet_uri)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
