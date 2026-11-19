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
    RunConfiguration,
    StartupConfiguration,
    SystemConfiguration,
    load_configuration,
    update_configuration_file,
    write_configuration_file,
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
            font_file_path=None,
            orientation=0,
            show_progress_bar=True,
            show_side_icons=True,
            show_volume_bar=True,
            target="pirateaudio",
            tick=0.5,
        )
        assert configuration.library == LibraryConfiguration(directory_path=Path("/music"))
        assert configuration.playback == PlaybackConfiguration(
            seek_step=10, volume_default=50, volume_step=5
        )
        assert configuration.run == RunConfiguration(mode="background")
        assert configuration.startup == StartupConfiguration(
            playlist="use_saved", state="use_saved", volume="use_saved"
        )
        assert configuration.system == SystemConfiguration(
            moc_state_on_exit="do_nothing",
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
                "brightness": 1.0,
                "font_file_path": None,
                "orientation": 0,
                "show_progress_bar": True,
                "show_side_icons": True,
                "show_volume_bar": True,
                "target": "pirateaudio",
                "tick": 0.5,
            },
            "library": {"directory_path": "/music"},
            "playback": {"seek_step": 10, "volume_default": 50, "volume_step": 5},
            "run": {"mode": "background"},
            "startup": {
                "playlist": "use_saved",
                "state": "use_saved",
                "volume": "use_saved",
            },
            "system": {
                "moc_state_on_exit": "do_nothing",
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
            "X_hold": "seek_forward",
            "Y": "volume_down",
            "Y_hold": "seek_backward",
        }

    def test_default_file_is_read(self, home):
        directory = home / ".config" / "mocassino"
        directory.mkdir(parents=True)
        (directory / "configuration.yaml").write_text(
            "playback:\n  volume_default: 30\n",
            encoding="utf-8",
        )
        assert load_configuration().playback.volume_default == 30

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
            "  brightness: 0.5\n"
            "  font_file_path: ~/font.ttf\n"
            "  show_side_icons: false\n"
            "  target: simulator\n"
            "  tick: 0.25\n"
            "library:\n"
            "  directory_path: /srv/music\n"
            "playback:\n"
            "  seek_step: 30\n"
            "  volume_default: 70\n"
            "  volume_step: 10\n"
            "run:\n"
            "  mode: foreground\n"
            "startup:\n"
            "  volume: use_default\n"
            "system:\n"
            "  moc_state_on_exit: quit\n"
            "  mocp_file_path: /usr/bin/mocp\n"
            "  shutdown_command: [systemctl, poweroff]\n",
        )
        assert load_configuration(path) == Configuration(
            buttons=ButtonsConfiguration(long_press_time=2.0, origin="none", repeat_hold_time=0.5),
            display=DisplayConfiguration(
                brightness=0.5,
                font_file_path=tmp_path / "font.ttf",
                show_side_icons=False,
                target="simulator",
                tick=0.25,
            ),
            library=LibraryConfiguration(directory_path=Path("/srv/music")),
            playback=PlaybackConfiguration(seek_step=30, volume_default=70, volume_step=10),
            run=RunConfiguration(mode="foreground"),
            startup=StartupConfiguration(volume="use_default"),
            system=SystemConfiguration(
                moc_state_on_exit="quit",
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
            ("display", "brightness", -0.1),
            ("display", "brightness", 1.1),
            ("display", "brightness", 2),
            ("display", "brightness", "bright"),
            ("display", "brightness", True),
            ("display", "font_file_path", 5),
            ("display", "orientation", 45),
            ("display", "orientation", 360),
            ("display", "orientation", -90),
            ("display", "orientation", "90"),
            ("display", "orientation", True),
            ("display", "show_progress_bar", "yes"),
            ("display", "show_side_icons", "yes"),
            ("display", "show_volume_bar", 0),
            ("display", "show_side_icons", 1),
            ("display", "target", "hdmi"),
            ("display", "tick", -0.5),
            ("library", "directory_path", 5),
            ("playback", "volume_default", -1),
            ("playback", "volume_default", 101),
            ("playback", "volume_default", 50.5),
            ("playback", "volume_default", True),
            ("playback", "seek_step", 0),
            ("playback", "seek_step", "far"),
            ("playback", "volume_step", 0),
            ("playback", "volume_step", 101),
            ("run", "mode", "window"),
            ("run", "mode", "Foreground"),
            ("run", "mode", True),
            ("startup", "playlist", "shuffle"),
            ("startup", "playlist", "saved"),
            ("startup", "playlist", "Use saved"),
            ("startup", "playlist", 5),
            ("startup", "state", "paused"),
            ("startup", "state", "use saved"),
            ("startup", "state", True),
            ("startup", "volume", "use_fallback"),
            ("startup", "volume", "Use saved"),
            ("startup", "volume", True),
            ("system", "moc_state_on_exit", "exit"),
            ("system", "moc_state_on_exit", "Do nothing"),
            ("system", "moc_state_on_exit", True),
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

    @pytest.mark.parametrize("playlist", ["open_library", "use_moc_state", "use_saved"])
    def test_startup_playlists(self, tmp_path, playlist):
        path = write_yaml(tmp_path, f"startup:\n  playlist: {playlist}\n")
        assert load_configuration(path).startup.playlist == playlist

    @pytest.mark.parametrize("state", ["pause", "play", "stop", "use_saved"])
    def test_startup_states(self, tmp_path, state):
        path = write_yaml(tmp_path, f"startup:\n  state: {state}\n")
        assert load_configuration(path).startup.state == state

    @pytest.mark.parametrize("volume", ["use_default", "use_saved"])
    def test_startup_volumes(self, tmp_path, volume):
        path = write_yaml(tmp_path, f"startup:\n  volume: {volume}\n")
        assert load_configuration(path).startup.volume == volume

    def test_startup_use_saved_volume_is_no_longer_a_key(self, tmp_path):
        path = write_yaml(tmp_path, "startup:\n  use_saved_volume: true\n")
        with pytest.raises(ConfigurationError, match="startup.use_saved_volume"):
            load_configuration(path)

    @pytest.mark.parametrize("orientation", [0, 90, 180, 270])
    def test_display_orientations(self, tmp_path, orientation):
        path = write_yaml(tmp_path, f"display:\n  orientation: {orientation}\n")
        assert load_configuration(path).display.orientation == orientation

    def test_display_bars(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "display:\n  show_progress_bar: false\n  show_volume_bar: false\n",
        )
        display = load_configuration(path).display
        assert (display.show_progress_bar, display.show_volume_bar) == (False, False)
        assert display.show_side_icons is True

    def test_invalid_yaml(self, tmp_path):
        with pytest.raises(ConfigurationError, match="is not valid YAML"):
            load_configuration(write_yaml(tmp_path, "library: [unclosed\n"))

    def test_no_file(self):
        assert load_configuration() == Configuration()

    def test_none_values_are_ignored(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "display:\n  font_file_path: null\nplayback:\n  volume_default: 30\n",
        )
        overrides = {"display": {"tick": None}, "playback": {"volume_default": None}}
        assert load_configuration(path, overrides) == Configuration(
            playback=PlaybackConfiguration(volume_default=30),
        )

    def test_not_a_mapping(self, tmp_path):
        with pytest.raises(ConfigurationError, match="must contain a mapping"):
            load_configuration(write_yaml(tmp_path, "- a\n- b\n"))

    def test_overrides_are_merged_per_section(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "buttons:\n  long_press_time: 2\nplayback:\n  seek_step: 30\n  volume_step: 3\n",
        )
        overrides = {
            "library": {"directory_path": Path("/other")},
            "playback": {"seek_step": 40},
        }
        assert load_configuration(path, overrides) == Configuration(
            buttons=ButtonsConfiguration(long_press_time=2.0),
            library=LibraryConfiguration(directory_path=Path("/other")),
            playback=PlaybackConfiguration(seek_step=40, volume_step=3),
        )

    def test_partial_section(self, tmp_path):
        path = write_yaml(tmp_path, "playback:\n  volume_default: 30\n")
        assert load_configuration(path) == Configuration(
            playback=PlaybackConfiguration(volume_default=30)
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


class TestUpdateConfigurationFile:
    """Tests for the update_configuration_file function"""

    def test_default_file_is_created(self, home):
        path = update_configuration_file(None, {"display": {"show_side_icons": False}})
        assert path == home / ".config" / "mocassino" / "configuration.yaml"
        assert path.read_text(encoding="utf-8") == "display:\n  show_side_icons: false\n"
        assert load_configuration().display.show_side_icons is False

    def test_existing_file_is_updated(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "# my settings\n"
            "playback:\n"
            "  volume_step: 3\n"
            "display:\n"
            "  tick: 0.25\n"
            "  show_side_icons: true\n"
            "library:\n"
            "  directory_path: /srv/musica/Andrè\n",
        )
        assert update_configuration_file(path, {"display": {"show_side_icons": False}}) == path
        assert path.read_text(encoding="utf-8") == (
            "playback:\n"
            "  volume_step: 3\n"
            "display:\n"
            "  tick: 0.25\n"
            "  show_side_icons: false\n"
            "library:\n"
            "  directory_path: /srv/musica/Andrè\n"
        )
        assert list(tmp_path.iterdir()) == [path]

    def test_file_cannot_be_written(self, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.touch()
        with pytest.raises(ConfigurationError, match="Cannot write configuration file"):
            update_configuration_file(blocker / "configuration.yaml", {"display": {}})

    def test_file_not_valid(self, tmp_path):
        path = write_yaml(tmp_path, "display: [unclosed\n")
        with pytest.raises(ConfigurationError, match="is not valid YAML"):
            update_configuration_file(path, {"display": {"show_side_icons": False}})
        assert path.read_text(encoding="utf-8") == "display: [unclosed\n"

    def test_section_empty_or_missing(self, tmp_path):
        path = write_yaml(tmp_path, "display:\n")
        update_configuration_file(path, {"buttons": {"origin": "none"}, "display": {"tick": 1.0}})
        assert load_configuration(path) == Configuration(
            buttons=ButtonsConfiguration(origin="none"),
            display=DisplayConfiguration(tick=1.0),
        )

    def test_section_not_a_mapping(self, tmp_path):
        path = write_yaml(tmp_path, "display: st7789\n")
        with pytest.raises(ConfigurationError, match="Section 'display' must be a mapping"):
            update_configuration_file(path, {"display": {"show_side_icons": False}})
        assert path.read_text(encoding="utf-8") == "display: st7789\n"


class TestWriteConfigurationFile:
    """Tests for the write_configuration_file function"""

    def test_default_file_is_created(self, home):
        path = write_configuration_file(None, Configuration())
        assert path == home / ".config" / "mocassino" / "configuration.yaml"
        assert load_configuration() == Configuration()

    def test_existing_file_is_replaced(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "# my settings\n"
            "display:\n"
            "  show_side_icons: false\n"
            "library:\n"
            "  directory_path: /srv/musica/Andrè\n",
        )
        configuration = Configuration(display=DisplayConfiguration(target="simulator"))
        assert write_configuration_file(path, configuration) == path
        content = path.read_text(encoding="utf-8")
        assert "# my settings" not in content
        assert "Andrè" not in content
        assert load_configuration(path) == configuration
        assert list(tmp_path.iterdir()) == [path]

    def test_keys_are_sorted(self, tmp_path):
        path = write_configuration_file(tmp_path / "configuration.yaml", Configuration())
        lines = path.read_text(encoding="utf-8").splitlines()
        sections = [line for line in lines if not line.startswith(" ")]
        assert sections == sorted(sections)

    def test_file_cannot_be_written(self, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.touch()
        with pytest.raises(ConfigurationError, match="Cannot write configuration file"):
            write_configuration_file(blocker / "configuration.yaml", Configuration())
