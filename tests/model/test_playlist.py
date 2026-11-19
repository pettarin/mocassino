"""Tests for the playlist of MOC.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.model.moc import MocState, MocStatus
from mocassino.model.playlist import list_tracks, playlist_fraction


def touch(path):
    """Create an empty file, and the directories leading to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


class TestListTracks:
    """Tests for the list_tracks function"""

    def test_directory(self, tmp_path):
        album = tmp_path / "Album"
        for name in (
            "02.mp3",
            "01.flac",
            "CD2/01.ogg",
            "CD1/02.wav",
            "CD1/01.FLAC",
            "cover.jpg",
            ".hidden.mp3",
            ".hidden/01.mp3",
            "notes.txt",
        ):
            touch(album / name)
        expected = ("01.flac", "02.mp3", "CD1/01.FLAC", "CD1/02.wav", "CD2/01.ogg")
        assert list_tracks(album) == tuple(str(album / name) for name in expected)

    def test_sorted_by_full_path(self, tmp_path):
        touch(tmp_path / "a b" / "1.mp3")
        touch(tmp_path / "a" / "2.mp3")
        touch(tmp_path / "a" / "b" / "3.mp3")
        tracks = list_tracks(tmp_path)
        assert tracks == tuple(sorted(tracks))
        assert len(tracks) == 3

    def test_file(self, tmp_path):
        track = touch(tmp_path / "01.flac")
        assert list_tracks(track) == (str(track),)

    def test_empty_directory(self, tmp_path):
        assert list_tracks(tmp_path) == ()

    def test_missing(self, tmp_path):
        assert list_tracks(tmp_path / "missing") == ()

    def test_directory_that_cannot_be_read(self, mocker, tmp_path, caplog):
        def walk(path, onerror):
            onerror(PermissionError(13, "Permission denied", str(path / "locked")))
            yield str(path), [], ["01.mp3"]

        mocker.patch("mocassino.model.playlist.os.walk", side_effect=walk)
        with caplog.at_level(logging.WARNING):
            assert list_tracks(tmp_path) == (str(tmp_path / "01.mp3"),)
        assert f"Cannot list '{tmp_path / 'locked'}'" in caplog.text


class TestPlaylistFraction:
    """Tests for the playlist_fraction function"""

    PLAYLIST = ("/music/1.mp3", "/music/2.mp3", "/music/3.mp3", "/music/4.mp3")

    @pytest.mark.parametrize(
        ("file_path", "current", "total", "fraction"),
        [
            ("/music/1.mp3", 0, 100, 0.25),
            ("/music/1.mp3", 50, 100, 0.25),
            ("/music/2.mp3", 30, None, 0.5),
            ("/music/3.mp3", 99, 100, 0.75),
            ("/music/4.mp3", 0, 100, 1.0),
            ("/music/4.mp3", 100, 100, 1.0),
        ],
    )
    def test_fraction(self, file_path, current, total, fraction):
        status = MocStatus(
            current_seconds=current,
            file_path=file_path,
            state=MocState.PLAY,
            total_seconds=total,
        )
        assert playlist_fraction(self.PLAYLIST, status) == pytest.approx(fraction)

    @pytest.mark.parametrize("file_path", ["", "/music/5.mp3", "http://example.com/stream"])
    def test_not_in_the_playlist(self, file_path):
        status = MocStatus(current_seconds=30, file_path=file_path, total_seconds=100)
        assert playlist_fraction(self.PLAYLIST, status) == 0.0

    def test_single_track(self):
        status = MocStatus(current_seconds=0, file_path="/music/1.mp3", total_seconds=100)
        assert playlist_fraction(("/music/1.mp3",), status) == 1.0

    def test_empty_playlist(self):
        status = MocStatus(current_seconds=30, file_path="/music/1.mp3", total_seconds=100)
        assert playlist_fraction((), status) == 0.0
