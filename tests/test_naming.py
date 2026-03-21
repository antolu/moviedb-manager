from __future__ import annotations

import pytest

from moviedb_manager.services.naming import ParsedFilename, parse_filename


@pytest.mark.parametrize(
    ("filename", "expected_name", "expected_year"),
    [
        ("Interstellar.2014.1080p.BluRay.x264.mkv", "Interstellar", "2014"),
        ("The.Dark.Knight.2008.720p.BluRay.mkv", "The Dark Knight", "2008"),
        ("Dune.Part.Two.2024.2160p.UHD.BluRay.mkv", "Dune Part Two", "2024"),
        ("Movie+Name.2020.1080p.mkv", "Movie Name", "2020"),
        ("2001.A.Space.Odyssey.1968.1080p.mkv", "2001 A Space Odyssey", "1968"),
        ("Classic.4k.2160p.mkv", "Classic 4k", ""),
        ("Old.Movie.480p.DVD.avi", "Old Movie", ""),
    ],
)
def test_parse_movie_filename(
    filename: str, expected_name: str, expected_year: str
) -> None:
    parsed = parse_filename(filename, "movie")
    assert parsed.name == expected_name
    assert parsed.year == expected_year


@pytest.mark.parametrize(
    (
        "filename",
        "expected_name",
        "expected_year",
        "expected_season",
        "expected_episode",
    ),
    [
        ("The.Mandalorian.S02E03.1080p.web.mp4", "The Mandalorian", "", 2, 3),
        ("Breaking.Bad.S05E14.Ozymandias.720p.mkv", "Breaking Bad", "", 5, 14),
        ("Shogun.2024.S01E01.mkv", "Shogun", "2024", 1, 1),
        ("The.Daily.Show.2024.03.20.1080p.mkv", "The Daily Show", "2024", None, None),
    ],
)
def test_parse_tv_filename(
    filename: str,
    expected_name: str,
    expected_year: str,
    expected_season: int,
    expected_episode: int,
) -> None:
    parsed = parse_filename(filename, "tv")
    assert parsed.name == expected_name
    assert parsed.year == expected_year
    assert parsed.season == expected_season
    assert parsed.episode == expected_episode


def test_parse_filename_no_year() -> None:
    parsed = parse_filename("Classic.Movie.mkv", "movie")
    assert parsed.name == "Classic Movie"
    assert not parsed.year


def test_parse_filename_no_episode_info() -> None:
    parsed = parse_filename("SomeShow.mkv", "tv")
    assert parsed.season is None
    assert parsed.episode is None


@pytest.mark.parametrize("ext", ["mkv", "mp4", "avi", "m4v"])
def test_parse_filename_common_extensions(ext: str) -> None:
    parsed = parse_filename(f"Movie.2023.1080p.{ext}", "movie")
    assert parsed.name == "Movie"
    assert parsed.year == "2023"


def test_parse_filename_scene_release() -> None:
    parsed = parse_filename("The.Batman.2022.1080p.BluRay.x264-SPARKS.mkv", "movie")
    assert parsed.name == "The Batman"
    assert parsed.year == "2022"


def test_parse_filename_returns_parsed_filename_model() -> None:
    result = parse_filename("Dune.2021.mkv", "movie")
    assert isinstance(result, ParsedFilename)
