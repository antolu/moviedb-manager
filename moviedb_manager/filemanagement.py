from __future__ import annotations

import errno
import os
import re
import shutil
import typing
from dataclasses import dataclass
from glob import escape, glob


@dataclass(slots=True)
class MediaInit:
    name: str
    magnet_uri: str
    data_root: str
    tmdb: typing.Any = None
    tvdb: typing.Any = None
    typ: str = "movie"


class Media:
    def __init__(self, config: dict[str, typing.Any], init: MediaInit) -> None:
        self.directories = config["directories"]
        self.tmdb = init.tmdb
        self.tvdb = init.tvdb
        self.typ = init.typ
        self.name = init.name
        self.magnet_uri = init.magnet_uri
        self.data_root = init.data_root
        self.type = init.typ

        self.mediafiles: list[MediaFile] = []
        self.media_extensions = config["misc"]["mediaextensions"]
        self.subtitle_extensions = config["misc"]["subtitleextensions"]

        self.__initialise_variables()

    def __initialise_variables(self) -> None:
        self.filename_regex = [
            re.compile(r"([\.\+]\d{4}[\.\+]\d{3,4}p[\.\+]).+"),
            re.compile(r"([\.\+]\d{4}[\.\+]).*"),
            re.compile(r"[\.\+]\d{3,4}p"),
            re.compile(r"(\d{4}[\.\+]\d{3,4}p[\.\+]).+"),
            re.compile(r"(\d{4}[\.\+]).*"),
            re.compile(r"[\.\+]\d{3,4}p"),
        ]
        self.year_regex = re.compile(r"(?:19|20)\d{2}")
        self.episode_regex = re.compile(r"S\d{2}E\d{2}")
        self.dotremove_regex = re.compile(r"[\.\+]")
        self.moved_to_library = False

    def process(self) -> None:
        self.data_path = os.path.join(
            self.directories["local"], self.directories["download"], self.data_root
        )

        if not os.path.exists(self.data_path):
            print("Cannot find downloaded files in " + self.name)

        if os.path.isdir(self.data_path):
            self.mediafiles = self.__find_mediafiles(self.data_path)
        else:
            for ext in self.media_extensions:
                candidate = self.data_path + ext
                if os.path.isfile(candidate):
                    self.mediafiles = [
                        MediaFile(os.path.basename(candidate), candidate, typ=self.type)
                    ]

        if self.mediafiles == []:
            print("No media files found")

        self.__find_name(self.mediafiles)
        self.__move_to_library()

        shutil.rmtree(self.data_path)

    def __find_mediafiles(
        self, data_path: str, files: list[MediaFile] | None = None
    ) -> list[MediaFile]:
        if files is None:
            files = []

        for ext in self.media_extensions:
            found = glob(os.path.join(escape(data_path), "*." + ext))
            for path in found:
                files.append(MediaFile(os.path.basename(path), path, typ="movie"))

        if files == []:
            for subfolder in os.listdir(data_path):
                subpath = os.path.join(data_path, subfolder)
                if os.path.isdir(subpath):
                    self.__find_mediafiles(subpath, files)

        return files

    def __process_filename(self, filename: str) -> dict[str, typing.Any]:
        res = None
        for regex in self.filename_regex:
            res = regex.search(filename)
            if res:
                break

        stripped_filename = filename.split(res.group(0))[0] if res else filename
        out: dict[str, typing.Any] = {
            "name": self.dotremove_regex.sub(" ", stripped_filename)
        }

        try:
            out["year"] = self.year_regex.findall(filename)[-1]
        except IndexError:
            out["year"] = ""
            print("could not find year data")

        if self.type == "tv":
            try:
                episode_data = self.episode_regex.findall(filename)[-1]
                out["season"] = int(episode_data[1:3])
                out["episode"] = int(episode_data[4:6])
                out["name"] = out["name"].split(episode_data)[0].rstrip()
            except IndexError:
                print("could not find episode data")

        return out

    def __find_name(self, mediafiles: list[MediaFile]) -> None:
        for mediafile in mediafiles:
            name_data = self.__process_filename(mediafile.filename)
            year = name_data["year"] or ""

            if self.type == "movie":
                res = self.tmdb.search(name_data["name"])
            else:
                search = self.tvdb.Search()
                res = search.series(name_data["name"])[0]
                tv_id = res["id"]

            if len(res) == 0:
                print("No results found")

            if self.type == "movie":
                metadata = None
                for item in res:
                    if item.release_date.startswith(year):
                        metadata = item
                        break

                if metadata is None:
                    metadata = res[0]

                title = (
                    f"{metadata.original_title} ({metadata.release_date.split('-')[0]})"
                )
                mediafile.metadata = metadata
            else:
                season = name_data["season"]
                episode = name_data["episode"]

                episode_no = f"S{season:02d}E{episode:02d}"
                show = self.tvdb.Series(tv_id)
                show.Episodes.update_filters(airedSeason=season, airedEpisode=episode)
                episode_name = show.Episodes.all()[0]["episodeName"]
                showname = show.info()["seriesName"]

                title = f"{showname} - {episode_no} - {episode_name}"
                mediafile.metadata = show
                mediafile.set_episode_data(season, episode)

            title = re.compile(r"\:").sub("", title)
            mediafile.set_realname(title)

    def __move_to_library(self) -> None:
        if self.moved_to_library:
            msg = "Already moved to library once!"
            raise OSError(msg)

        if self.type == "movie":
            dest = os.path.join(self.directories["local"], self.directories["movie"])
        else:
            dest = os.path.join(self.directories["local"], self.directories["tv"])

        for mediafile in self.mediafiles:
            mediafile.rename(mediafile.realname or mediafile.filename)
            if self.type == "tv":
                season, _ = mediafile.get_episode_data()
                showname = mediafile.metadata.seriesName
                series_dest = os.path.join(dest, showname, f"Season {season}")
                mediafile.move(series_dest)
            else:
                mediafile.move(dest)

        self.moved_to_library = True

    def move_to(self, new_dir: str) -> None:
        for mediafile in self.mediafiles:
            mediafile.move(new_dir)


def mkdir_p(path: str) -> None:
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class AbstractFile:
    def __init__(
        self,
        filename: str,
        absolutepath: str,
        children: list[AbstractFile] | None = None,
        childpath: str = "Subtitles",
    ) -> None:
        if children is None:
            children = []
        self.filename = filename
        self.absolutepath = absolutepath
        self.extension = os.path.splitext(os.path.basename(filename))[1]
        self.children = children
        self.childpath = childpath
        self.season: int | None = None
        self.episode: int | None = None

    def move(self, dest: str) -> None:
        mkdir_p(dest)
        newpath = os.path.join(dest, self.filename + self.extension)
        os.rename(self.absolutepath, newpath)
        self.absolutepath = newpath

        for child in self.children:
            child.move(os.path.join(dest, self.childpath))

    def rename(self, newname: str) -> None:
        name = newname + self.extension
        dest = os.path.split(self.absolutepath)[0]
        newpath = os.path.join(dest, name)
        os.rename(self.absolutepath, newpath)
        self.filename = name
        self.absolutepath = newpath

        for child in self.children:
            child.rename(newname)

    def set_episode_data(self, season: int, episode: int) -> None:
        self.season = season
        self.episode = episode

    def get_episode_data(self) -> tuple[int | None, int | None]:
        return self.season, self.episode


class MediaFile(AbstractFile):
    def __init__(
        self,
        filename: str,
        absolutepath: str,
        realname: str | None = None,
        typ: str = "movie",
        subtitle_path: str = "Subtitles",
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(filename, absolutepath, childpath=subtitle_path)
        self.realname = realname
        self.metadata: typing.Any = None
        self.type = typ

    def set_realname(self, realname: str) -> None:
        self.realname = realname

        for sub in self.children:
            if type(sub) is not SubtitleFile:
                msg = f"{sub} is not of type SubtitleFile"
                raise AssertionError(msg)
            sub.realname = realname

    def add_subtitle(self, subtitle: SubtitleFile) -> None:
        if type(subtitle) is not SubtitleFile:
            msg = f"{subtitle} is not of type SubtitleFile"
            raise TypeError(msg)

        self.children.append(subtitle)


class SubtitleFile(AbstractFile):
    def __init__(
        self, filename: str, absolutepath: str, realname: str | None = None
    ) -> None:
        super().__init__(filename, absolutepath)
        self.realname = realname
