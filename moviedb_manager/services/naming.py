from __future__ import annotations

import re
import typing

import pydantic

if typing.TYPE_CHECKING:
    from ..models.media import MediaType


class ParsedFilename(pydantic.BaseModel):
    name: str
    year: str = ""
    season: int | None = None
    episode: int | None = None


FILENAME_REGEXES = [
    re.compile(r"([\.\+]\d{4}[\.\+]\d{3,4}p([\.\+]|$)).*"),
    re.compile(r"([\.\+]\d{4}([\.\+]|$)).*"),
    re.compile(r"[\.\+]\d{3,4}p"),
    re.compile(r"(\d{4}[\.\+]\d{3,4}p([\.\+]|$)).*"),
    re.compile(r"(\d{4}([\.\+]|$)).*"),
    re.compile(r"[\.\+]\d{3,4}p"),
]
YEAR_REGEX = re.compile(r"(?:19|20)\d{2}")
EPISODE_REGEX = re.compile(r"S\d{2}E\d{2}")
DOTREMOVE_REGEX = re.compile(r"[\.\+]")


def parse_filename(filename: str, media_type: MediaType) -> ParsedFilename:
    # Strip extension
    base_filename = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", filename)

    res = None
    for regex in FILENAME_REGEXES:
        res = regex.search(base_filename)
        if res:
            break

    stripped_filename = (
        base_filename.split(res.group(0), maxsplit=1)[0] if res else base_filename
    )
    name = DOTREMOVE_REGEX.sub(" ", stripped_filename).strip()

    try:
        year = YEAR_REGEX.findall(base_filename)[-1]
    except IndexError:
        year = ""

    season = None
    episode = None
    if media_type == "tv":
        try:
            episode_data = EPISODE_REGEX.findall(filename)[-1]
            season = int(episode_data[1:3])
            episode = int(episode_data[4:6])
            name = name.split(episode_data)[0].rstrip()
        except IndexError:
            pass

    return ParsedFilename(name=name, year=year, season=season, episode=episode)
