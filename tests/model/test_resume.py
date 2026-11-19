"""Tests for resuming the saved playback.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.model.moc import MocError, MocState
from mocassino.model.resume import (
    POLL_ATTEMPTS,
    SEEK_ATTEMPTS,
    adopt_playback,
    resume_playback,
)
from mocassino.model.state_file import SavedState
from tests.model.fake_moc import FakeMoc


@pytest.fixture
def album(tmp_path):
    """Create an album of five tracks."""
    album = tmp_path / "music" / "Album"
    album.mkdir(parents=True)
    for number in range(1, 6):
        (album / f"0{number}.flac").touch()
    return album


@pytest.fixture
def pauses():
    """Collect the pauses asked while resuming, instead of really waiting."""
    return []


def saved(album, track: str = "03.flac", **values) -> SavedState:
    """Build the saved state of an album being played."""
    values.setdefault("seek", 95)
    values.setdefault("state", MocState.PLAY)
    return SavedState(directory_path=str(album), file_path=str(album / track), **values)


class TestAdoptPlayback:
    """Tests for the adopt_playback function"""

    def test_moc_playing_from_the_saved_directory(self, album):
        moc = FakeMoc()
        moc.play(album)
        moc.pause()
        moc.calls.clear()
        assert adopt_playback(moc, saved(album)) == str(album)
        assert moc.calls == [("status", None)]
        assert moc.state is MocState.PAUSE

    def test_moc_playing_something_else(self, album, tmp_path):
        other = tmp_path / "other.flac"
        other.touch()
        moc = FakeMoc()
        moc.play(other)
        assert adopt_playback(moc, saved(album)) is None

    def test_moc_stopped(self, album):
        assert adopt_playback(FakeMoc(), saved(album)) is None

    def test_nothing_saved(self, album):
        moc = FakeMoc()
        moc.play(album)
        assert adopt_playback(moc, SavedState(volume=85)) is None


class TestResumePlayback:
    """Tests for the resume_playback function"""

    def test_first_track(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, saved(album, "01.flac"), pauses.append) == str(album)
        assert moc.names() == ["set_volume", "play", "jump"]
        assert (moc.index, moc.seconds, moc.state) == (0, 95, MocState.PLAY)

    def test_moc_already_playing_from_the_saved_directory(self, album, pauses):
        moc = FakeMoc()
        moc.play(album)
        moc.calls.clear()
        assert resume_playback(moc, saved(album), pauses.append) == str(album)
        assert moc.names() == []
        assert (moc.index, moc.seconds) == (0, 0)

    def test_moc_already_playing_something_else(self, album, tmp_path, pauses):
        other = tmp_path / "other.flac"
        other.touch()
        moc = FakeMoc()
        moc.play(other)
        moc.pause()
        moc.calls.clear()
        assert resume_playback(moc, saved(album), pauses.append) is None
        assert moc.names() == []
        assert moc.state is MocState.PAUSE

    def test_moc_error_stops_the_playback(self, album, pauses):
        moc = FakeMoc(fails_on="jump")
        with pytest.raises(MocError, match="jump failed"):
            resume_playback(moc, saved(album), pauses.append)
        assert moc.names()[-2:] == ["jump", "stop"]
        assert moc.state is MocState.STOP

    def test_nothing_saved(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, SavedState(volume=85), pauses.append) is None
        assert resume_playback(moc, SavedState(file_path="/music/a.flac"), pauses.append) is None
        assert resume_playback(moc, SavedState(directory_path="/music"), pauses.append) is None
        assert moc.calls == []

    def test_paused(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, saved(album, state=MocState.PAUSE), pauses.append) == str(album)
        assert moc.names() == ["set_volume", "play", "next", "next", "jump", "pause"]
        assert (moc.index, moc.seconds, moc.state) == (2, 95, MocState.PAUSE)

    def test_playing(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, saved(album), pauses.append) == str(album)
        assert moc.calls[:3] == [("status", None), ("set_volume", 0), ("play", str(album))]
        assert moc.names() == ["set_volume", "play", "next", "next", "jump"]
        assert (moc.index, moc.seconds, moc.state) == (2, 95, MocState.PLAY)
        assert moc.volume == 0

    def test_position_at_the_start(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, saved(album, seek=0), pauses.append) == str(album)
        assert moc.names() == ["set_volume", "play", "next", "next"]

    def test_position_cannot_be_reached(self, album, pauses, caplog):
        moc = FakeMoc(ignored_jumps=SEEK_ATTEMPTS)
        with caplog.at_level(logging.WARNING):
            assert resume_playback(moc, saved(album), pauses.append) == str(album)
        assert "cannot be reached" in caplog.text
        assert moc.names().count("jump") == SEEK_ATTEMPTS
        assert (moc.index, moc.seconds, moc.state) == (2, 0, MocState.PLAY)

    def test_position_reached_at_the_second_attempt(self, album, pauses):
        moc = FakeMoc(ignored_jumps=1)
        assert resume_playback(moc, saved(album), pauses.append) == str(album)
        assert moc.names().count("jump") == 2
        assert moc.seconds == 95

    def test_single_file(self, album, pauses):
        track = str(album / "04.flac")
        state = SavedState(directory_path=track, file_path=track, seek=10, state=MocState.PLAY)
        moc = FakeMoc()
        assert resume_playback(moc, state, pauses.append) == track
        assert moc.names() == ["set_volume", "play", "jump"]
        assert moc.tracks == [track]

    def test_stopped(self, album, pauses):
        moc = FakeMoc()
        assert resume_playback(moc, saved(album, state=MocState.STOP), pauses.append) is None
        assert moc.names() == []

    def test_track_changes_are_waited_for(self, album, pauses):
        moc = FakeMoc(lag=3)
        assert resume_playback(moc, saved(album), pauses.append) == str(album)
        assert (moc.index, moc.seconds) == (2, 95)
        assert len(pauses) >= 9

    def test_track_missing(self, album, pauses, caplog):
        moc = FakeMoc()
        with caplog.at_level(logging.WARNING):
            assert resume_playback(moc, saved(album, "09.flac"), pauses.append) is None
        assert "cannot be resumed" in caplog.text
        assert moc.names() == []

    def test_track_not_in_the_directory(self, album, tmp_path, pauses):
        other = tmp_path / "other.flac"
        other.touch()
        state = SavedState(directory_path=str(album), file_path=str(other), state=MocState.PLAY)
        moc = FakeMoc()
        assert resume_playback(moc, state, pauses.append) is None
        assert moc.names() == []

    def test_track_not_in_the_playlist(self, album, pauses, caplog):
        (album / "notes.txt").touch()
        moc = FakeMoc()
        moc.play = lambda path: (
            FakeMoc.play(moc, path) or moc.tracks.remove(str(album / "notes.txt"))
        )
        with caplog.at_level(logging.WARNING):
            assert resume_playback(moc, saved(album, "notes.txt"), pauses.append) is None
        assert "is not in" in caplog.text
        assert moc.names()[-1] == "stop"
        assert moc.names().count("next") == 5
        assert len(pauses) == POLL_ATTEMPTS - 1

    def test_track_not_reached_when_moc_does_not_advance(self, album, pauses):
        moc = FakeMoc(stuck=True)
        assert resume_playback(moc, saved(album), pauses.append) is None
        assert moc.names() == ["set_volume", "play", "next", "stop"]

    def test_track_not_reached_when_the_playlist_repeats(self, album, pauses):
        (album / "notes.txt").touch()
        moc = FakeMoc(repeat=True)
        moc.play = lambda path: (
            FakeMoc.play(moc, path) or moc.tracks.remove(str(album / "notes.txt"))
        )
        assert resume_playback(moc, saved(album, "notes.txt"), pauses.append) is None
        assert moc.names().count("next") == 5
        assert moc.names()[-1] == "stop"

    def test_track_too_far(self, album, pauses, mocker):
        mocker.patch("mocassino.model.resume.MAX_SKIPS", 2)
        moc = FakeMoc()
        assert resume_playback(moc, saved(album, "05.flac"), pauses.append) is None
        assert moc.names() == ["set_volume", "play", "next", "next", "stop"]
