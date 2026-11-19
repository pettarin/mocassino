"""Tests for the configuration module.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from pathlib import Path

import pytest

from mocassino.configuration import (
    ButtonsConfiguration,
    Configuration,
    ConfigurationError,
    DisplayConfiguration,
    LibraryConfiguration,
    PlaybackConfiguration,
    SystemConfiguration,
    load_configuration,
)
from mocassino.controller.actions import DEFAULT_BUTTON_MAP


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point the home directory to a temporary one, so the user's files are never read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def write_yaml(directory: Path, content: str) -> Path:
    """Write a YAML configuration file and return its path."""
    path = directory / "custom.yaml"
    path.write_text(content, encoding="utf-8")
    return path


class TestConfiguration:
    """Tests for the Configuration class"""

    def test_defaults(self):
        configuration = Configuration()
        assert configuration.buttons == ButtonsConfiguration(hold_time=1.0, origin="gpio")
        assert configuration.display == DisplayConfiguration(
            font_file_path=None, target="st7789", tick=0.5
        )
        assert configuration.library == LibraryConfiguration(directory_path=Path("/music"))
        assert configuration.playback == PlaybackConfiguration(initial_volume=50, volume_step=5)
        assert configuration.system == SystemConfiguration(
            mocp_file_path="mocp",
            shutdown_command=("sudo", "shutdown", "-h", "now"),
        )

    def test_to_dict(self):
        assert Configuration().to_dict() == {
            "buttons": {
                "button_map": DEFAULT_BUTTON_MAP,
                "hold_time": 1.0,
                "origin": "gpio",
            },
            "display": {"font_file_path": None, "target": "st7789", "tick": 0.5},
            "library": {"directory_path": "/music"},
            "playback": {"initial_volume": 50, "volume_step": 5},
            "system": {
                "mocp_file_path": "mocp",
                "shutdown_command": ["sudo", "shutdown", "-h", "now"],
            },
        }

    def test_to_dict_with_font_file_path(self):
        configuration = Configuration(
            display=DisplayConfiguration(font_file_path=Path("/fonts/a.ttf"))
        )
        assert configuration.to_dict()["display"]["font_file_path"] == "/fonts/a.ttf"


class TestLoadConfiguration:
    """Tests for the load_configuration function"""

    def test_button_map(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "buttons:\n  button_map:\n    playback:\n      B: previous\n      B_long: null\n",
        )
        button_map = load_configuration(path).buttons.button_map
        assert button_map["menu"] == DEFAULT_BUTTON_MAP["menu"]
        assert button_map["playback"] == {
            "A": "play_pause",
            "A_long": "open_menu",
            "B": "previous",
            "X": "volume_up",
            "Y": "volume_down",
        }

    def test_default_file_is_read(self, home):
        directory = home / ".config" / "mocassino"
        directory.mkdir(parents=True)
        (directory / "configuration.yaml").write_text(
            "playback:\n  initial_volume: 30\n",
            encoding="utf-8",
        )
        assert load_configuration().playback.initial_volume == 30

    def test_empty_file(self, tmp_path):
        assert load_configuration(write_yaml(tmp_path, "")) == Configuration()

    def test_empty_section(self, tmp_path):
        assert (
            load_configuration(write_yaml(tmp_path, "buttons:\nplayback: {}\n")) == Configuration()
        )

    def test_explicit_file(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "buttons:\n"
            "  hold_time: 2\n"
            "  origin: none\n"
            "display:\n"
            "  font_file_path: ~/font.ttf\n"
            "  target: simulator\n"
            "  tick: 0.25\n"
            "library:\n"
            "  directory_path: /srv/music\n"
            "playback:\n"
            "  initial_volume: 70\n"
            "  volume_step: 10\n"
            "system:\n"
            "  mocp_file_path: /usr/bin/mocp\n"
            "  shutdown_command: [systemctl, poweroff]\n",
        )
        assert load_configuration(path) == Configuration(
            buttons=ButtonsConfiguration(hold_time=2.0, origin="none"),
            display=DisplayConfiguration(
                font_file_path=tmp_path / "font.ttf", target="simulator", tick=0.25
            ),
            library=LibraryConfiguration(directory_path=Path("/srv/music")),
            playback=PlaybackConfiguration(initial_volume=70, volume_step=10),
            system=SystemConfiguration(
                mocp_file_path="/usr/bin/mocp",
                shutdown_command=("systemctl", "poweroff"),
            ),
        )

    def test_explicit_file_missing(self, tmp_path):
        with pytest.raises(ConfigurationError, match="Cannot read configuration file"):
            load_configuration(tmp_path / "missing.yaml")

    @pytest.mark.parametrize(
        ("section", "key", "value"),
        [
            ("buttons", "button_map", "A"),
            ("buttons", "button_map", {"menu": {"A": "rewind"}}),
            ("buttons", "hold_time", 0),
            ("buttons", "hold_time", "long"),
            ("buttons", "hold_time", True),
            ("buttons", "origin", "keyboard"),
            ("buttons", "origin", 5),
            ("display", "font_file_path", 5),
            ("display", "target", "hdmi"),
            ("display", "tick", -0.5),
            ("library", "directory_path", 5),
            ("playback", "initial_volume", -1),
            ("playback", "initial_volume", 101),
            ("playback", "initial_volume", 50.5),
            ("playback", "initial_volume", True),
            ("playback", "volume_step", 0),
            ("playback", "volume_step", 101),
            ("system", "mocp_file_path", ["mocp"]),
            ("system", "shutdown_command", "'unbalanced"),
            ("system", "shutdown_command", ""),
            ("system", "shutdown_command", ["shutdown", 0]),
            ("system", "shutdown_command", 5),
        ],
    )
    def test_invalid_value(self, section, key, value):
        with pytest.raises(ConfigurationError, match=f"Invalid value for '{section}.{key}'"):
            load_configuration(overrides={section: {key: value}})

    def test_invalid_yaml(self, tmp_path):
        with pytest.raises(ConfigurationError, match="is not valid YAML"):
            load_configuration(write_yaml(tmp_path, "library: [unclosed\n"))

    def test_no_file(self):
        assert load_configuration() == Configuration()

    def test_none_values_are_ignored(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "display:\n  font_file_path: null\nplayback:\n  initial_volume: 30\n",
        )
        overrides = {"display": {"tick": None}, "playback": {"initial_volume": None}}
        assert load_configuration(path, overrides) == Configuration(
            playback=PlaybackConfiguration(initial_volume=30),
        )

    def test_not_a_mapping(self, tmp_path):
        with pytest.raises(ConfigurationError, match="must contain a mapping"):
            load_configuration(write_yaml(tmp_path, "- a\n- b\n"))

    def test_overrides_are_merged_per_section(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "buttons:\n  hold_time: 2\nplayback:\n  initial_volume: 30\n  volume_step: 2\n",
        )
        overrides = {
            "library": {"directory_path": Path("/other")},
            "playback": {"initial_volume": 40},
        }
        assert load_configuration(path, overrides) == Configuration(
            buttons=ButtonsConfiguration(hold_time=2.0),
            library=LibraryConfiguration(directory_path=Path("/other")),
            playback=PlaybackConfiguration(initial_volume=40, volume_step=2),
        )

    def test_partial_section(self, tmp_path):
        path = write_yaml(tmp_path, "playback:\n  initial_volume: 30\n")
        assert load_configuration(path) == Configuration(
            playback=PlaybackConfiguration(initial_volume=30)
        )

    def test_section_not_a_mapping(self, tmp_path):
        with pytest.raises(ConfigurationError, match="Section 'buttons' must be a mapping"):
            load_configuration(write_yaml(tmp_path, "buttons: gpio\n"))

    def test_shutdown_command_as_string(self):
        overrides = {"system": {"shutdown_command": "sudo shutdown -h 'now'"}}
        configuration = load_configuration(overrides=overrides)
        assert configuration.system.shutdown_command == ("sudo", "shutdown", "-h", "now")

    def test_unknown_keys(self, tmp_path):
        path = write_yaml(tmp_path, "buttons:\n  zoom: 2\ncolour: red\nextras:\n  a: 1\n")
        with pytest.raises(
            ConfigurationError,
            match="Unknown configuration keys: buttons.zoom, colour, extras",
        ):
            load_configuration(path)
