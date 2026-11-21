"""Tests for the state file.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.model.moc import MocState
from mocassino.model.state_file import SavedState, StateFile

FULL = (
    "playback:\n"
    "    state: playing                           # or paused or stopped\n"
    '    directory_path: "/music/Artist/Album"\n'
    '    file_path: "/music/Artist/Album/003_Track.flac"\n'
    "    seek: 95                         # e.g. 1:35 into the track\n"
    "    volume: 85\n"
)
FULL_STATE = SavedState(
    directory_path="/music/Artist/Album",
    file_path="/music/Artist/Album/003_Track.flac",
    seek=95,
    state=MocState.PLAY,
    volume=85,
)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point the home directory to a temporary one, so the user's files are never touched."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def path(tmp_path):
    return tmp_path / "custom" / "state.yaml"


def write(path, content: str) -> None:
    """Write the state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestSavedState:
    """Tests for the SavedState class"""

    def test_defaults(self):
        assert SavedState() == SavedState(
            directory_path=None,
            file_path=None,
            seek=0,
            state=MocState.STOP,
            volume=None,
        )


class TestStateFile:
    """Tests for the StateFile class"""

    def test_default_path(self, home):
        assert StateFile().path == home / ".mocassino" / "state.yaml"

    def test_load(self, path):
        write(path, FULL)
        assert StateFile(path).load() == FULL_STATE

    @pytest.mark.parametrize(
        ("name", "state"),
        [("paused", MocState.PAUSE), ("playing", MocState.PLAY), ("stopped", MocState.STOP)],
    )
    def test_load_states(self, path, name, state):
        write(path, f"playback:\n  state: {name}\n")
        assert StateFile(path).load() == SavedState(state=state)

    def test_load_blank_values(self, path, caplog):
        write(
            path,
            "playback:\n"
            "  directory_path: null\n"
            "  file_path: null\n"
            "  seek: 0\n"
            "  state: stopped\n"
            "  volume: 50\n",
        )
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState(volume=50)
        assert caplog.text == ""

    @pytest.mark.parametrize("content", ["", "- 85\n", "playback: 85\n", "volume: 85\n"])
    def test_load_no_playback(self, path, caplog, content):
        write(path, content)
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState()
        assert "has no playback state" in caplog.text

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("directory_path", "5"),
            ("directory_path", "''"),
            ("file_path", "[a, b]"),
            ("seek", "-1"),
            ("seek", "soon"),
            ("seek", "true"),
            ("state", "rewinding"),
            ("state", "5"),
            ("volume", "loud"),
            ("volume", "true"),
            ("volume", "85.5"),
            ("volume", "-1"),
            ("volume", "101"),
        ],
    )
    def test_load_value_not_valid(self, path, caplog, key, value):
        write(path, FULL + f"    {key}: {value}\n")
        expected = {
            "directory_path": FULL_STATE.directory_path,
            "file_path": FULL_STATE.file_path,
            "seek": FULL_STATE.seek,
            "state": FULL_STATE.state,
            "volume": FULL_STATE.volume,
        }
        expected[key] = getattr(SavedState(), key)
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState(**expected)
        assert f"has no valid {key}" in caplog.text

    def test_load_volume_only(self, path, caplog):
        write(path, "playback:\n    volume: 85     # 85% of the volume\n")
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState(volume=85)
        assert caplog.text == ""

    def test_load_without_file(self, path, caplog):
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState()
        assert caplog.text == ""

    def test_load_yaml_not_valid(self, path, caplog):
        write(path, "playback: [unclosed\n")
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load() == SavedState()
        assert "Cannot read the state file" in caplog.text

    def test_path(self, path):
        assert StateFile(path).path == path

    def test_save(self, path):
        state_file = StateFile(path)
        assert state_file.save(FULL_STATE) is True
        assert path.read_text(encoding="utf-8") == (
            "playback:\n"
            "  directory_path: /music/Artist/Album\n"
            "  file_path: /music/Artist/Album/003_Track.flac\n"
            "  seek: 95\n"
            "  state: playing\n"
            "  volume: 85\n"
        )
        assert list(path.parent.iterdir()) == [path]
        assert StateFile(path).load() == FULL_STATE

    def test_save_blank_values(self, path):
        assert StateFile(path).save(SavedState(volume=50)) is True
        assert path.read_text(encoding="utf-8") == (
            "playback:\n"
            "  directory_path: null\n"
            "  file_path: null\n"
            "  seek: 0\n"
            "  state: stopped\n"
            "  volume: 50\n"
        )
        assert StateFile(path).load() == SavedState(volume=50)

    def test_save_cannot_write(self, tmp_path, caplog):
        blocker = tmp_path / "blocker"
        blocker.touch()
        state_file = StateFile(blocker / "state.yaml")
        with caplog.at_level(logging.ERROR):
            assert state_file.save(FULL_STATE) is False
        assert "Cannot write the state file" in caplog.text

    def test_save_keeps_accented_paths_readable(self, path):
        state = SavedState(directory_path="/music/Andrè", file_path="/music/Andrè/a.flac")
        StateFile(path).save(state)
        assert "/music/Andrè/a.flac" in path.read_text(encoding="utf-8")
        assert StateFile(path).load() == state

    def test_save_only_changes(self, path):
        state_file = StateFile(path)
        assert state_file.save(FULL_STATE) is True
        path.write_text("touched\n", encoding="utf-8")
        assert state_file.save(FULL_STATE) is False
        assert path.read_text(encoding="utf-8") == "touched\n"
        assert state_file.save(SavedState(volume=86)) is True
        assert "volume: 86" in path.read_text(encoding="utf-8")

    def test_save_what_was_loaded_does_not_write(self, path):
        write(path, FULL)
        state_file = StateFile(path)
        assert state_file.load() == FULL_STATE
        assert state_file.save(FULL_STATE) is False
        assert path.read_text(encoding="utf-8") == FULL

    def test_save_what_was_loaded_writes_if_something_was_not_valid(self, path):
        write(path, FULL + "    seek: soon\n")
        state_file = StateFile(path)
        loaded = state_file.load()
        assert loaded.seek == 0
        assert state_file.save(loaded) is True
        assert "seek: 0" in path.read_text(encoding="utf-8")
