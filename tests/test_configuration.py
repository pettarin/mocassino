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
        assert configuration.buttons == ButtonsConfiguration(
            long_press_time=0.6, origin="pirateaudio", repeat_hold_time=0.3
        )
        assert configuration.display == DisplayConfiguration(
            font_file_path=None, show_side_icons=True, target="pirateaudio", tick=0.5
        )
        assert configuration.library == LibraryConfiguration(directory_path=Path("/music"))
        assert configuration.playback == PlaybackConfiguration(
            initial_volume=50, seek_step=10, volume_step=2
        )
        assert configuration.system == SystemConfiguration(
            mocp_file_path="mocp",
            shutdown_command=("sudo", "shutdown", "-h", "now"),
        )

    def test_to_dict(self):
        assert Configuration().to_dict() == {
            "buttons": {
                "button_map": DEFAULT_BUTTON_MAP,
                "long_press_time": 0.6,
                "origin": "pirateaudio",
                "repeat_hold_time": 0.3,
            },
            "display": {
                "font_file_path": None,
                "show_side_icons": True,
                "target": "pirateaudio",
                "tick": 0.5,
            },
            "library": {"directory_path": "/music"},
            "playback": {"initial_volume": 50, "seek_step": 10, "volume_step": 2},
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
            "buttons:\n  button_map:\n    playback:\n      B: previous\n      B_hold: null\n",
        )
        button_map = load_configuration(path).buttons.button_map
        assert button_map["menu"] == DEFAULT_BUTTON_MAP["menu"]
        assert button_map["playback"] == {
            "A": "play_pause",
            "A_long": "open_menu",
            "B": "previous",
            "X": "volume_up",
            "X_hold": "seek_forward",
            "Y": "volume_down",
            "Y_hold": "seek_backward",
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
            "  long_press_time: 2\n"
            "  origin: none\n"
            "  repeat_hold_time: 0.5\n"
            "display:\n"
            "  font_file_path: ~/font.ttf\n"
            "  show_side_icons: false\n"
            "  target: simulator\n"
            "  tick: 0.25\n"
            "library:\n"
            "  directory_path: /srv/music\n"
            "playback:\n"
            "  initial_volume: 70\n"
            "  seek_step: 30\n"
            "  volume_step: 10\n"
            "system:\n"
            "  mocp_file_path: /usr/bin/mocp\n"
            "  shutdown_command: [systemctl, poweroff]\n",
        )
        assert load_configuration(path) == Configuration(
            buttons=ButtonsConfiguration(long_press_time=2.0, origin="none", repeat_hold_time=0.5),
            display=DisplayConfiguration(
                font_file_path=tmp_path / "font.ttf",
                show_side_icons=False,
                target="simulator",
                tick=0.25,
            ),
            library=LibraryConfiguration(directory_path=Path("/srv/music")),
            playback=PlaybackConfiguration(initial_volume=70, seek_step=30, volume_step=10),
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
            ("buttons", "long_press_time", 0),
            ("buttons", "long_press_time", "long"),
            ("buttons", "long_press_time", True),
            ("buttons", "origin", "keyboard"),
            ("buttons", "origin", 5),
            ("buttons", "repeat_hold_time", 0),
            ("buttons", "repeat_hold_time", "fast"),
            ("display", "font_file_path", 5),
            ("display", "show_side_icons", "yes"),
            ("display", "show_side_icons", 1),
            ("display", "target", "hdmi"),
            ("display", "tick", -0.5),
            ("library", "directory_path", 5),
            ("playback", "initial_volume", -1),
            ("playback", "initial_volume", 101),
            ("playback", "initial_volume", 50.5),
            ("playback", "initial_volume", True),
            ("playback", "seek_step", 0),
            ("playback", "seek_step", "far"),
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

    @pytest.mark.parametrize("origin", ["gpio", "none", "pirateaudio", "simulator"])
    def test_buttons_origins(self, origin):
        configuration = load_configuration(overrides={"buttons": {"origin": origin}})
        assert configuration.buttons.origin == origin

    @pytest.mark.parametrize("target", ["none", "pirateaudio", "simulator", "st7789"])
    def test_display_targets(self, target):
        configuration = load_configuration(overrides={"display": {"target": target}})
        assert configuration.display.target == target

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
            "buttons:\n  long_press_time: 2\nplayback:\n  initial_volume: 30\n  volume_step: 3\n",
        )
        overrides = {
            "library": {"directory_path": Path("/other")},
            "playback": {"initial_volume": 40},
        }
        assert load_configuration(path, overrides) == Configuration(
            buttons=ButtonsConfiguration(long_press_time=2.0),
            library=LibraryConfiguration(directory_path=Path("/other")),
            playback=PlaybackConfiguration(initial_volume=40, volume_step=3),
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
