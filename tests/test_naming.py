from __future__ import annotations

from moviedb_manager.services.naming import parse_filename


def test_parse_movie_filename() -> None:
    filename = "Interstellar.2014.1080p.BluRay.x264.mkv"
    parsed = parse_filename(filename, "movie")
    assert parsed.name == "Interstellar"
    assert parsed.year == "2014"


def test_parse_tv_filename() -> None:
    filename = "The.Mandalorian.S02E03.1080p.web.mp4"
    parsed = parse_filename(filename, "tv")
    assert parsed.name == "The Mandalorian"
    assert parsed.season == 2  # noqa: PLR2004
    assert parsed.episode == 3  # noqa: PLR2004


def test_parse_filename_no_year() -> None:
    filename = "Classic.Movie.mkv"
    parsed = parse_filename(filename, "movie")
    assert parsed.name == "Classic Movie"
    assert not parsed.year


def test_parse_filename_with_dots_and_pluses() -> None:
    filename = "Movie+Name.2020.mkv"
    parsed = parse_filename(filename, "movie")
    assert parsed.name == "Movie Name"
