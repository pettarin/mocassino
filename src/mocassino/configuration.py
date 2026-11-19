"""Configuration of the service: defaults, YAML file, and overrides.

The settings are grouped in sections, one per concern:
buttons, display, library, playback, and system.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import shlex
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mocassino.controller.actions import resolve_button_map

BUTTONS_ORIGINS: tuple[str, ...] = ("gpio", "none", "simulator")
DEFAULT_CONFIGURATION_FILE_PATH: Path = Path("~/.config/mocassino/configuration.yaml")
DISPLAY_TARGETS: tuple[str, ...] = ("none", "simulator", "st7789")


@dataclass(frozen=True)
class ButtonsConfiguration:
    """The settings of the buttons.

    The button map is in plain form: see the actions module of the controller.
    """

    button_map: dict[str, dict[str, str]] = field(default_factory=lambda: resolve_button_map({}))
    long_press_time: float = 0.6
    origin: str = "gpio"
    repeat_hold_time: float = 0.3


class ConfigurationError(Exception):
    """Raised when the configuration cannot be read or is not valid."""


@dataclass(frozen=True)
class DisplayConfiguration:
    """The settings of the display."""

    font_file_path: Path | None = None
    target: str = "st7789"
    tick: float = 0.5


@dataclass(frozen=True)
class LibraryConfiguration:
    """The settings of the music library."""

    directory_path: Path = Path("/music")


@dataclass(frozen=True)
class PlaybackConfiguration:
    """The settings of the playback."""

    initial_volume: int = 50
    seek_step: int = 10
    volume_step: int = 2


@dataclass(frozen=True)
class SystemConfiguration:
    """The settings of the host system."""

    mocp_file_path: str = "mocp"
    shutdown_command: tuple[str, ...] = ("sudo", "shutdown", "-h", "now")


@dataclass(frozen=True)
class Configuration:
    """The permanent settings of the service, grouped in sections.

    Defined after the sections, as it refers to them.
    """

    buttons: ButtonsConfiguration = field(default_factory=ButtonsConfiguration)
    display: DisplayConfiguration = field(default_factory=DisplayConfiguration)
    library: LibraryConfiguration = field(default_factory=LibraryConfiguration)
    playback: PlaybackConfiguration = field(default_factory=PlaybackConfiguration)
    system: SystemConfiguration = field(default_factory=SystemConfiguration)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Return the settings as nested dictionaries of plain (YAML-friendly) values."""
        values: dict[str, dict[str, Any]] = asdict(self)
        font_file_path = self.display.font_file_path
        values["display"]["font_file_path"] = (
            None if font_file_path is None else str(font_file_path)
        )
        values["library"]["directory_path"] = str(self.library.directory_path)
        values["system"]["shutdown_command"] = list(self.system.shutdown_command)
        return values


def _build(*sources: Mapping[str, Any]) -> Configuration:
    """Build a validated Configuration from nested raw values.

    The sources are merged section by section, the later ones taking precedence;
    values set to None are ignored, and missing keys take their defaults.
    """
    coercers: dict[str, dict[str, Callable[[Any], Any]]] = {
        "buttons": {
            "button_map": resolve_button_map,
            "long_press_time": _to_float,
            "origin": _to_str,
            "repeat_hold_time": _to_float,
        },
        "display": {"font_file_path": _to_path, "target": _to_str, "tick": _to_float},
        "library": {"directory_path": _to_path},
        "playback": {
            "initial_volume": _to_int,
            "seek_step": _to_int,
            "volume_step": _to_int,
        },
        "system": {"mocp_file_path": _to_str, "shutdown_command": _to_command},
    }
    merged: dict[str, dict[str, Any]] = {section: {} for section in coercers}
    unknown: set[str] = set()
    for source in sources:
        for section, content in source.items():
            if section not in coercers:
                unknown.add(str(section))
            elif isinstance(content, Mapping):
                for key, value in content.items():
                    if key not in coercers[section]:
                        unknown.add(f"{section}.{key}")
                    elif value is not None:
                        merged[section][key] = value
            elif content is not None:
                raise ConfigurationError(f"Section '{section}' must be a mapping")
    if unknown:
        raise ConfigurationError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    for section, content in merged.items():
        for key, value in content.items():
            try:
                content[key] = coercers[section][key](value)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"Invalid value for '{section}.{key}': {value!r} ({exc})"
                ) from exc
    configuration = Configuration(
        buttons=ButtonsConfiguration(**merged["buttons"]),
        display=DisplayConfiguration(**merged["display"]),
        library=LibraryConfiguration(**merged["library"]),
        playback=PlaybackConfiguration(**merged["playback"]),
        system=SystemConfiguration(**merged["system"]),
    )
    checks: dict[str, tuple[object, bool]] = {
        "buttons.long_press_time": (
            configuration.buttons.long_press_time,
            configuration.buttons.long_press_time > 0,
        ),
        "buttons.origin": (
            configuration.buttons.origin,
            configuration.buttons.origin in BUTTONS_ORIGINS,
        ),
        "buttons.repeat_hold_time": (
            configuration.buttons.repeat_hold_time,
            configuration.buttons.repeat_hold_time > 0,
        ),
        "display.target": (
            configuration.display.target,
            configuration.display.target in DISPLAY_TARGETS,
        ),
        "display.tick": (configuration.display.tick, configuration.display.tick > 0),
        "playback.initial_volume": (
            configuration.playback.initial_volume,
            0 <= configuration.playback.initial_volume <= 100,
        ),
        "playback.seek_step": (
            configuration.playback.seek_step,
            configuration.playback.seek_step >= 1,
        ),
        "playback.volume_step": (
            configuration.playback.volume_step,
            1 <= configuration.playback.volume_step <= 100,
        ),
    }
    for name, (value, valid) in checks.items():
        if not valid:
            raise ConfigurationError(f"Invalid value for '{name}': {value!r}")
    return configuration


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read the mapping stored in a YAML configuration file."""
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"Cannot read configuration file '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Configuration file '{path}' is not valid YAML: {exc}") from exc
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigurationError(f"Configuration file '{path}' must contain a mapping")
    return {str(key): value for key, value in content.items()}


def _to_command(value: object) -> tuple[str, ...]:
    """Coerce a string or a list of strings to a command line."""
    if isinstance(value, str):
        parts = tuple(shlex.split(value))
    elif isinstance(value, list | tuple) and all(isinstance(part, str) for part in value):
        parts = tuple(value)
    else:
        raise TypeError("expected a string or a list of strings")
    if not parts:
        raise ValueError("expected a non-empty command")
    return parts


def _to_float(value: object) -> float:
    """Coerce a number to a float."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError("expected a number")
    return float(value)


def _to_int(value: object) -> int:
    """Coerce an integer to an int."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("expected an integer")
    return value


def _to_path(value: object) -> Path:
    """Coerce a string or a path to a Path, expanding the home directory."""
    if not isinstance(value, str | Path):
        raise TypeError("expected a path")
    return Path(value).expanduser()


def _to_str(value: object) -> str:
    """Coerce a string to a str."""
    if not isinstance(value, str):
        raise TypeError("expected a string")
    return value


def load_configuration(
    path: Path | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Configuration:
    """Load the configuration.

    The values come, in increasing order of precedence, from: the defaults,
    the YAML file, and the overrides (e.g., the command line options).
    The overrides have the same nested shape as the YAML file
    (e.g., ``{"buttons": {"origin": "none"}}``).
    Values set to None are ignored.

    :param path: the YAML file; if None, the default one is read, if it exists
    :param overrides: the values taking precedence over those in the YAML file
    :raises ConfigurationError: if the file cannot be read or a value is not valid
    """
    values: dict[str, Any] = {}
    if path is not None:
        values = _read_yaml(path)
    elif DEFAULT_CONFIGURATION_FILE_PATH.expanduser().is_file():
        values = _read_yaml(DEFAULT_CONFIGURATION_FILE_PATH.expanduser())
    return _build(values, overrides or {})
