"""Tests for the state file.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.model.state_file import StateFile


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point the home directory to a temporary one, so the user's files are never touched."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def path(tmp_path):
    return tmp_path / "custom" / "state.yaml"


class TestStateFile:
    """Tests for the StateFile class"""

    def test_default_path(self, home):
        assert StateFile().path == home / ".config" / "mocassino" / "state.yaml"

    def test_load_volume(self, path):
        path.parent.mkdir()
        path.write_text("playback:\n    volume: 85     # 85% of the volume\n", encoding="utf-8")
        assert StateFile(path).load_volume() == 85

    @pytest.mark.parametrize(
        "content",
        [
            "",
            "- 85\n",
            "playback: 85\n",
            "playback:\n  position: 3\n",
            "playback:\n  volume: loud\n",
            "playback:\n  volume: true\n",
            "playback:\n  volume: 85.5\n",
            "playback:\n  volume: -1\n",
            "playback:\n  volume: 101\n",
        ],
    )
    def test_load_volume_not_valid(self, path, caplog, content):
        path.parent.mkdir()
        path.write_text(content, encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load_volume() is None
        assert "has no valid volume" in caplog.text

    def test_load_volume_without_file(self, path, caplog):
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load_volume() is None
        assert caplog.text == ""

    def test_load_volume_yaml_not_valid(self, path, caplog):
        path.parent.mkdir()
        path.write_text("playback: [unclosed\n", encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            assert StateFile(path).load_volume() is None
        assert "Cannot read the state file" in caplog.text

    def test_path(self, path):
        assert StateFile(path).path == path

    def test_save(self, path):
        state_file = StateFile(path)
        assert state_file.save(85) is True
        assert path.read_text(encoding="utf-8") == "playback:\n  volume: 85\n"
        assert list(path.parent.iterdir()) == [path]
        assert StateFile(path).load_volume() == 85

    def test_save_cannot_write(self, tmp_path, caplog):
        blocker = tmp_path / "blocker"
        blocker.touch()
        state_file = StateFile(blocker / "state.yaml")
        with caplog.at_level(logging.ERROR):
            assert state_file.save(85) is False
        assert "Cannot write the state file" in caplog.text

    def test_save_only_changes(self, path):
        state_file = StateFile(path)
        assert state_file.save(85) is True
        path.write_text("touched\n", encoding="utf-8")
        assert state_file.save(85) is False
        assert path.read_text(encoding="utf-8") == "touched\n"
        assert state_file.save(86) is True
        assert path.read_text(encoding="utf-8") == "playback:\n  volume: 86\n"

    def test_save_what_was_loaded_does_not_write(self, path):
        path.parent.mkdir()
        original = "playback:\n    volume: 85     # 85% of the volume\n"
        path.write_text(original, encoding="utf-8")
        state_file = StateFile(path)
        assert state_file.load_volume() == 85
        assert state_file.save(85) is False
        assert path.read_text(encoding="utf-8") == original
        assert state_file.save(80) is True
        assert path.read_text(encoding="utf-8") == "playback:\n  volume: 80\n"
