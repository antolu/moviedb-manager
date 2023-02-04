import re
import errno
import os
import shutil
from glob import glob, escape
from requests.exceptions import HTTPError


# TODO: logger

class Media:
    def __init__(self, config, name, magnet_uri, data_root, tmdb=None, tvdb=None, typ='movie'):
        super().__init__()
        self.directories = config['directories']
        self.tmdb = tmdb
        self.tvdb = tvdb
        self.typ = typ
        self.name = name
        self.magnet_uri = magnet_uri
        self.mediafiles = []
        self.data_root = data_root
        self.type = typ

        self.media_extensions = config['misc']['mediaextensions']
        self.subtitle_extensions = config['misc']['subtitleextensions']

        self.__initialise_variables()

    def __initialise_variables(self):
            # .2019.1080p.XXXXX , .2019.XXXXX , .1080p.XXXXX
        # 2019.1080p.XXXXX , 2019.XXXXX , 1080p.XXXXX
        self.filename_regex = [
            re.compile(r"([\.\+]\d{4}[\.\+]\d{3,4}p[\.\+]).+"),
            re.compile(r"([\.\+]\d{4}[\.\+]).*"), 
            re.compile(r"[\.\+]\d{3,4}p"),
            re.compile(r"(\d{4}[\.\+]\d{3,4}p[\.\+]).+"), 
            re.compile(r"(\d{4}[\.\+]).*"), 
            re.compile(r"[\.\+]\d{3,4}p")
        ]

        self.year_regex = re.compile(r'(?:19|20)\d{2}')
        self.episode_regex = re.compile(r"S\d{2}E\d{2}")

        self.dotremove_regex = re.compile(r"[\.\+]")

        self.moved_to_library = False

    def process(self):

        # find file
        self.data_path = os.path.join(self.directories["local"], self.directories["download"], self.data_root)

        if not os.path.exists(self.data_path):
            print("Cannot find downloaded files in " + self.name)

        if os.path.isdir(self.data_path):
            self.mediafiles = self.__find_mediafiles(self.data_path)
        else:
            for ext in self.media_extensions:
                candidate = self.data_path + ext
                if os.path.isfile(candidate):
                    self.mediafiles = [
                        MediaFile(os.path.basename(candidate), candidate, self.type)]

        if self.mediafiles == []:
            print("No media files found")
            # TODO: aise some exception

        self.__find_name(self.mediafiles)
        self.__move_to_library()

        shutil.rmtree(self.data_path)


    def __find_mediafiles(self, data_path : str, files=[]):

        for ext in self.media_extensions:
            found = glob(os.path.join(escape(data_path), "*." + ext))
            for f in found:
                files.append(MediaFile(os.path.basename(f), f, typ='movie'))
                # TODO: find subtitles

        if files == []:
            for subfolder in os.listdir(data_path):
                self.__find_mediafiles(subfolder, files)

        return files


    def __process_filename(self, filename : str):
        """
        Extracts useful information from the filename of a media file like real name,
        episode data.

        TODO: 
        Parameters
        ----------
        filename : str
            The original filename of a media, eg. The.Mandalorian.S01E01.x264.WEBRIP.mkv

        Returns
        -------
        dict
            A dictionary containing keys 'name', 'year', 'season', 'episode', where applicable. 
        """
        for r in self.filename_regex:
            res = r.search(filename)  # strip filename

            if res:
                break

        stripped_filename = filename.split(res.group(0))[0]

        out = {"name": self.dotremove_regex.sub(" ", stripped_filename)}

        try:
            year = self.year_regex.findall(filename)[-1]
            out["year"] = year
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


    def __find_name(self, mediafiles : list):

        for f in mediafiles:
            name_data = self.__process_filename(f.filename)

            year = name_data["year"]
            year = year if year != "" else ""

            if self.type == 'movie':
                res = self.tmdb.search(name_data["name"])
            elif self.type == 'tv':
                search = self.tvdb.Search()
                res = search.series(name_data["name"])[0]
                tv_id = res["id"]

            if len(res) == 0:
                print("No results found")

            if self.type == "movie":
                # filter results by year
                for item in res:
                    if item.release_date.startswith(year):
                        title = item.title
                        metadata = item
                        break

                title = "{} ({})".format(metadata.original_title, metadata.release_date.split('-')[0])

                f.metadata = metadata
            elif self.type == "tv":
                #TODO: add year check

                season = name_data["season"]
                episode = name_data["episode"]

                episode_no= "S{:02d}E{:02d}".format(season, episode)
                show = self.tvdb.Series(tv_id)

                show.Episodes.update_filters(airedSeason=season, airedEpisode=episode)
                episode_name = show.Episodes.all()[0]["episodeName"]
                showname = show.info()["seriesName"]

                title = "{} - {} - {}".format(showname, episode_no, episode_name)

                f.metadata = show
                f.set_episode_data(season, episode)

            regex = re.compile(r'\:') # remove illegal characters
            title = regex.sub('', title)

            f.set_realname(title)


    def __move_to_library(self):
        if self.moved_to_library:
            raise EnvironmentError("Already moved to library once!")

        if self.type == "movie":
            dest = os.path.join(self.directories['local'],
                        self.directories['movie'])
        elif self.type == "tv":
            dest = os.path.join(self.directories['local'],
                        self.directories['tv'])

        for f in self.mediafiles:
            f.rename(f.realname)
            if self.type == "tv":
                season, _ = f.episode_data
                showname = f.metadata.seriesName

                series_dest = os.path.join(dest, showname, "Season {}".format(season))
                f.move(series_dest)
            else:
                f.move(dest)

        self.moved_to_library = True


    def move_to(self, new_dir):
        for f in self.mediafiles:
            f.move(new_dir)


def mkdir_p(path):
    # https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise



class AbstractFile:
    def __init__(self, filename, absolutepath, children=[], childpath="Subtitles"):
        self.filename = filename
        self.absolutepath = absolutepath
        self.extension = os.path.splitext(os.path.basename(filename))[1]
        
        self.children = children
        self.childpath = childpath

        self.season = None
        self.episode = None

    def move(self, dest):
        
        mkdir_p(dest)

        newpath = os.path.join(dest, self.filename + self.extension)
        
        os.rename(self.absolutepath, os.path.join(dest, self.filename + self.extension))
        self.absolutepath = newpath

        for child in self.children:
            child.move(self, os.path.join(dest, self.childpath))
    
    def rename(self, newname, keep_ext=True):
        
        if keep_ext:
            name = newname + self.extension
        
        dest = os.path.split(self.absolutepath)[0]

        newpath = os.path.join(dest, name)

        os.rename(self.absolutepath, newpath)
        self.filename = name
        self.absolutepath = newpath

        for child in self.children:
            child.rename(newname, keep_ext=keep_ext)

    def set_episode_data(self, season, episode):
        self.season = season
        self.episode = episode

    def get_episode_data(self):
        return self.season, self.episode
    
    episode_data = property(get_episode_data, set_episode_data, "Episode data")




class MediaFile(AbstractFile):
    def __init__(self, filename, absolutepath, realname=None, typ='movie', subtitle_path="Subtitles", **kwargs):
        super().__init__(filename, absolutepath, childpath=subtitle_path)
        self.realname = realname
        self.metadata = None
        self.type = typ
    
    def set_realname(self, realname):
        self.realname = realname
        
        for sub in self.children:
            if type(sub) is not SubtitleFile:
                raise AssertionError(f"{sub} is not of type SubtitleFile")
            sub.realname = realname

    def add_subtitle(self, subtitle):
        if type(subtitle) is not SubtitleFile:
            raise TypeError(f"{subtitle} is not of type SubtitleFile")

        self.children.append(subtitle)


class SubtitleFile(AbstractFile):
    def __init__(self, filename, absolutepath, realname=None):
        super().__init__(filename, absolutepath)
        self.realname = realname
