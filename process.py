import os
from time import sleep

from filemanagement import Media
from celery import Celery


@celery.task
def process(self, magnet_uri: str, typ: str, config):
    client = config["qbittorrent"]
    tmdb = config["tmdb"]
    tvdb = config["tvdb"]

    d = config["directories"]


    res = client.torrents_add(
        urls=[magnet_uri], save_path=os.path.join(d['remote'], d["download"]), is_paused=True)

    if res != "Ok.":
        print("Torrent add failed: {}".format(res))

    torrent_list = client.torrents_info(status_filter='paused')

    active_torrents = {}

    torrent = None

    for torrent in torrent_list:
        if torrent["magnet_uri"] not in active_torrents:
            obj = {
                'name': torrent['name'],
                'magnet_uri': torrent['magnet_uri'],
                'hash': torrent['hash']
            }
            client.torrents_resume(obj['hash'])
            active_torrents[obj['magnet_uri']] = obj
            if torrent["magnet_uri"] == magnet_uri:
                torrent = obj

    print("Torrent in progress")
    while client.torrents_info(hash=torrent["hash"])[0]["state"] != "uploading":
        sleep(1)

    # this assumes that the 0th file is in the root directory of the download
    torrent['data_root'] = os.path.split(
        client.torrents_files(hash=torrent['hash'])[0]["name"])[0]
    client.torrents_delete(delete_files=False, hashes=torrent['hash'])

    print("Torrent complete")

    # TODO: look for media files inside local dir
    # TODO: move files asynchronously

    media = Media(config, torrent["name"], torrent["magnet_uri"],
                torrent["data_root"], tmdb, tvdb, typ=typ)

    media.process()

    return True
