"""Configuration of the service: defaults, YAML file, and overrides.

The settings are grouped in sections, one per concern:
buttons, display, library, playback, run, startup, and system.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import shlex
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from mocassino.constants import (
    DISPLAY_TIMEOUT_CHOICES,
    ORIENTATIONS,
    VOLUME_MAX,
    VOLUME_MIN,
    ButtonsOrigin,
    DisplayTarget,
    MocStateOnExit,
    RunMode,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.controller.actions import resolve_button_map
from mocassino.defaults import (
    DEFAULT_BUTTONS_LONG_PRESS_TIME,
    DEFAULT_BUTTONS_ORIGIN,
    DEFAULT_BUTTONS_REPEAT_HOLD_TIME,
    DEFAULT_COLOR_SPECS,
    DEFAULT_CONFIGURATION_FILE_PATH,
    DEFAULT_DISPLAY_BRIGHTNESS,
    DEFAULT_DISPLAY_FONT_FILE_PATH,
    DEFAULT_DISPLAY_ORIENTATION,
    DEFAULT_DISPLAY_TARGET,
    DEFAULT_DISPLAY_TICK,
    DEFAULT_DISPLAY_TIMEOUT,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_TIMERS,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR,
    DEFAULT_LIBRARY_DIRECTORY_PATH,
    DEFAULT_PLAYBACK_SEEK_STEP,
    DEFAULT_PLAYBACK_VOLUME_DEFAULT,
    DEFAULT_PLAYBACK_VOLUME_STEP,
    DEFAULT_RUN_MODE,
    DEFAULT_STARTUP_PLAYLIST,
    DEFAULT_STARTUP_STATE,
    DEFAULT_STARTUP_VOLUME,
    DEFAULT_SYSTEM_MOC_STATE_ON_EXIT,
    DEFAULT_SYSTEM_MOCP_FILE_PATH,
    DEFAULT_SYSTEM_REBOOT_COMMAND,
    DEFAULT_SYSTEM_SHUTDOWN_COMMAND,
)
from mocassino.model.colors import parse_color


@dataclass(frozen=True)
class ButtonsConfiguration:
    """The settings of the buttons.

    The button map is in plain form: see the actions module of the controller.
    """

    button_map: dict[str, dict[str, str]] = field(default_factory=lambda: resolve_button_map({}))
    long_press_time: float = DEFAULT_BUTTONS_LONG_PRESS_TIME
    origin: str = DEFAULT_BUTTONS_ORIGIN
    repeat_hold_time: float = DEFAULT_BUTTONS_REPEAT_HOLD_TIME


class ConfigurationError(Exception):
    """Raised when the configuration cannot be read or is not valid."""


class ConfigurationReadError(ConfigurationError):
    """Raised when the configuration file cannot be read (e.g., it does not exist)."""


@dataclass(frozen=True)
class ColorsConfiguration:
    """The colors of the display, each a name (e.g., "white") or an HTML code (e.g., "#FFF").

    See the Colors class of the view for the role of each color.
    """

    accented: str = DEFAULT_COLOR_SPECS["accented"]
    background: str = DEFAULT_COLOR_SPECS["background"]
    muted: str = DEFAULT_COLOR_SPECS["muted"]
    normal: str = DEFAULT_COLOR_SPECS["normal"]
    track: str = DEFAULT_COLOR_SPECS["track"]


@dataclass(frozen=True)
class UiElementsConfiguration:
    """Which elements are shown on the display in playback mode.

    Defined before the settings of the display, as they refer to it.
    The playlist bar and the volume bar are shown only if the side icons are too.
    """

    show_playlist_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR
    show_progress_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR
    show_side_icons: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS
    show_timers: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_TIMERS
    show_volume_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR


@dataclass(frozen=True)
class DisplayConfiguration:
    """The settings of the display."""

    brightness: float = DEFAULT_DISPLAY_BRIGHTNESS
    colors: ColorsConfiguration = field(default_factory=ColorsConfiguration)
    font_file_path: Path | None = DEFAULT_DISPLAY_FONT_FILE_PATH
    orientation: int = DEFAULT_DISPLAY_ORIENTATION
    target: str = DEFAULT_DISPLAY_TARGET
    tick: float = DEFAULT_DISPLAY_TICK
    timeout: int = DEFAULT_DISPLAY_TIMEOUT
    ui_elements: UiElementsConfiguration = field(default_factory=UiElementsConfiguration)


@dataclass(frozen=True)
class LibraryConfiguration:
    """The settings of the music library.

    The default music root directory is expanded (e.g., "~" to "/home/pi") when these
    settings are made, as are the paths read from the configuration file.
    """

    directory_path: Path = field(default_factory=DEFAULT_LIBRARY_DIRECTORY_PATH.expanduser)


@dataclass(frozen=True)
class PlaybackConfiguration:
    """The settings of the playback."""

    seek_step: int = DEFAULT_PLAYBACK_SEEK_STEP
    volume_default: int = DEFAULT_PLAYBACK_VOLUME_DEFAULT
    volume_step: int = DEFAULT_PLAYBACK_VOLUME_STEP


@dataclass(frozen=True)
class RunConfiguration:
    """The settings of how the service is run.

    The mode tells whether the service runs in background or in foreground,
    unless the command line says otherwise.
    """

    mode: str = DEFAULT_RUN_MODE


@dataclass(frozen=True)
class StartupConfiguration:
    """The settings of what the service does when it starts."""

    playlist: str = DEFAULT_STARTUP_PLAYLIST
    state: str = DEFAULT_STARTUP_STATE
    volume: str = DEFAULT_STARTUP_VOLUME


@dataclass(frozen=True)
class SystemConfiguration:
    """The settings of the host system."""

    moc_state_on_exit: str = DEFAULT_SYSTEM_MOC_STATE_ON_EXIT
    mocp_file_path: str = DEFAULT_SYSTEM_MOCP_FILE_PATH
    reboot_command: tuple[str, ...] = DEFAULT_SYSTEM_REBOOT_COMMAND
    shutdown_command: tuple[str, ...] = DEFAULT_SYSTEM_SHUTDOWN_COMMAND


@dataclass(frozen=True)
class Configuration:
    """The permanent settings of the service, grouped in sections.

    Defined after the sections, as it refers to them.
    """

    buttons: ButtonsConfiguration = field(default_factory=ButtonsConfiguration)
    display: DisplayConfiguration = field(default_factory=DisplayConfiguration)
    library: LibraryConfiguration = field(default_factory=LibraryConfiguration)
    playback: PlaybackConfiguration = field(default_factory=PlaybackConfiguration)
    run: RunConfiguration = field(default_factory=RunConfiguration)
    startup: StartupConfiguration = field(default_factory=StartupConfiguration)
    system: SystemConfiguration = field(default_factory=SystemConfiguration)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Return the settings as nested dictionaries of plain (YAML-friendly) values."""
        values: dict[str, dict[str, Any]] = asdict(self)
        font_file_path = self.display.font_file_path
        values["display"]["font_file_path"] = (
            None if font_file_path is None else str(font_file_path)
        )
        values["library"]["directory_path"] = str(self.library.directory_path)
        values["system"]["reboot_command"] = list(self.system.reboot_command)
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
        "display": {
            "brightness": _to_float,
            "colors": _to_colors,
            "font_file_path": _to_path,
            "orientation": _to_int,
            "target": _to_str,
            "tick": _to_float,
            "timeout": _to_int,
            "ui_elements": _to_ui_elements,
        },
        "library": {"directory_path": _to_path},
        "playback": {
            "seek_step": _to_int,
            "volume_default": _to_int,
            "volume_step": _to_int,
        },
        "run": {"mode": _to_str},
        "startup": {
            "playlist": _to_str,
            "state": _to_str,
            "volume": _to_str,
        },
        "system": {
            "moc_state_on_exit": _to_str,
            "mocp_file_path": _to_str,
            "reboot_command": _to_command,
            "shutdown_command": _to_command,
        },
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
        run=RunConfiguration(**merged["run"]),
        startup=StartupConfiguration(**merged["startup"]),
        system=SystemConfiguration(**merged["system"]),
    )
    checks: dict[str, tuple[object, bool]] = {
        "buttons.long_press_time": (
            configuration.buttons.long_press_time,
            configuration.buttons.long_press_time > 0,
        ),
        "buttons.origin": (
            configuration.buttons.origin,
            configuration.buttons.origin in list(ButtonsOrigin),
        ),
        "buttons.repeat_hold_time": (
            configuration.buttons.repeat_hold_time,
            configuration.buttons.repeat_hold_time > 0,
        ),
        "display.brightness": (
            configuration.display.brightness,
            0.0 <= configuration.display.brightness <= 1.0,
        ),
        "display.orientation": (
            configuration.display.orientation,
            configuration.display.orientation in ORIENTATIONS,
        ),
        "display.timeout": (
            configuration.display.timeout,
            configuration.display.timeout in DISPLAY_TIMEOUT_CHOICES,
        ),
        "display.target": (
            configuration.display.target,
            configuration.display.target in list(DisplayTarget),
        ),
        "display.tick": (configuration.display.tick, configuration.display.tick > 0),
        "playback.seek_step": (
            configuration.playback.seek_step,
            configuration.playback.seek_step >= 1,
        ),
        "playback.volume_default": (
            configuration.playback.volume_default,
            VOLUME_MIN <= configuration.playback.volume_default <= VOLUME_MAX,
        ),
        "playback.volume_step": (
            configuration.playback.volume_step,
            1 <= configuration.playback.volume_step <= VOLUME_MAX,
        ),
        "run.mode": (
            configuration.run.mode,
            configuration.run.mode in list(RunMode),
        ),
        "startup.playlist": (
            configuration.startup.playlist,
            configuration.startup.playlist in list(StartupPlaylist),
        ),
        "startup.state": (
            configuration.startup.state,
            configuration.startup.state in list(StartupState),
        ),
        "startup.volume": (
            configuration.startup.volume,
            configuration.startup.volume in list(StartupVolume),
        ),
        "system.moc_state_on_exit": (
            configuration.system.moc_state_on_exit,
            configuration.system.moc_state_on_exit in list(MocStateOnExit),
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
        raise ConfigurationReadError(f"Cannot read configuration file '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Configuration file '{path}' is not valid YAML: {exc}") from exc
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigurationError(f"Configuration file '{path}' must contain a mapping")
    return {str(key): value for key, value in content.items()}


def _to_bool(value: object) -> bool:
    """Coerce a boolean to a bool."""
    if not isinstance(value, bool):
        raise TypeError("expected true or false")
    return value


def _to_color(value: object) -> str:
    """Check that a value is a color, a name or an HTML code, and return it as it is.

    :raises ValueError: if the value is not a color
    """
    if not isinstance(value, str):
        raise ValueError(f"expected a color name or an HTML code, not {value!r}")
    parse_color(value)
    return value


def _to_colors(value: object) -> ColorsConfiguration:
    """Coerce a mapping of colors, each a name or an HTML code, to the colors of the display.

    The colors missing, or set to None, take their defaults.

    :raises ConfigurationError: if a color is unknown or not valid
    :raises TypeError: if the value is not a mapping
    """
    coercers = dict.fromkeys(DEFAULT_COLOR_SPECS, _to_color)
    return ColorsConfiguration(**_to_nested(value, "display.colors", coercers))


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


def _to_nested(
    value: object,
    name: str,
    coercers: Mapping[str, Callable[[Any], Any]],
) -> dict[str, Any]:
    """Coerce a mapping nested in a section (e.g., display.colors), key by key.

    The keys set to None are left out, so that they take their defaults.

    :param name: the full name of the mapping, for the errors (e.g., "display.colors")
    :param coercers: how to coerce the value of each known key
    :raises ConfigurationError: if a key is unknown, or its value is not valid
    :raises TypeError: if the value is not a mapping
    """
    if not isinstance(value, Mapping):
        raise TypeError("expected a mapping")
    unknown = sorted(f"{name}.{key}" for key in value if key not in coercers)
    if unknown:
        raise ConfigurationError(f"Unknown configuration keys: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for key, item in value.items():
        if item is None:
            continue
        try:
            values[key] = coercers[key](item)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid value for '{name}.{key}': {item!r} ({exc})") from exc
    return values


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


def _to_ui_elements(value: object) -> UiElementsConfiguration:
    """Coerce a mapping of booleans to the elements shown on the display.

    The elements missing, or set to None, take their defaults.

    :raises ConfigurationError: if an element is unknown, or its value is not a boolean
    :raises TypeError: if the value is not a mapping
    """
    coercers = dict.fromkeys(asdict(UiElementsConfiguration()), _to_bool)
    return UiElementsConfiguration(**_to_nested(value, "display.ui_elements", coercers))


def _write_yaml(target: Path, content: Mapping[str, Any], sort_keys: bool) -> None:
    """Write the content to the YAML file, through a temporary file replacing it at once.

    :raises ConfigurationError: if the file cannot be written
    """
    temporary = target.with_name(f"{target.name}.tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            yaml.safe_dump(dict(content), allow_unicode=True, sort_keys=sort_keys),
            encoding="utf-8",
        )
        temporary.replace(target)
    except OSError as exc:
        raise ConfigurationError(f"Cannot write configuration file '{target}': {exc}") from exc


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


def replace_invalid_configuration_file(
    path: Path | None,
    defaults: Configuration,
    now: datetime | None = None,
) -> Path:
    """Move the configuration file to a backup next to it, and write the defaults in its place.

    The backup is named after the file and the time, e.g., configuration.yaml.20261119153000.bak,
    so that the older backups are kept; if one with the same name exists,
    a counter is added to the time, e.g., configuration.yaml.20261119153000-1.bak.

    :param path: the YAML file; if None, the default one
    :param defaults: the configuration to write in place of the file
    :param now: the time of the backup; if None, the current one
    :return: the backup
    :raises ConfigurationError: if the file cannot be moved, or the defaults cannot be written
    """
    target = DEFAULT_CONFIGURATION_FILE_PATH.expanduser() if path is None else path
    stamp = (datetime.now() if now is None else now).strftime("%Y%m%d%H%M%S")
    backup = target.with_name(f"{target.name}.{stamp}.bak")
    counter = 0
    while backup.exists():
        counter += 1
        backup = target.with_name(f"{target.name}.{stamp}-{counter}.bak")
    try:
        target.rename(backup)
    except OSError as exc:
        raise ConfigurationError(
            f"Cannot move configuration file '{target}' to '{backup}': {exc}"
        ) from exc
    write_configuration_file(target, defaults)
    return backup


def simulated_defaults(buttons: bool, display: bool) -> Configuration:
    """Return the default configuration, with the simulator for the buttons and the display.

    :param buttons: whether the buttons are simulated, instead of the default origin
    :param display: whether the display is simulated, instead of the default target
    """
    defaults = Configuration()
    if buttons:
        defaults = replace(
            defaults, buttons=replace(defaults.buttons, origin=ButtonsOrigin.SIMULATOR.value)
        )
    if display:
        defaults = replace(
            defaults, display=replace(defaults.display, target=DisplayTarget.SIMULATOR.value)
        )
    return defaults


def update_configuration_file(
    path: Path | None,
    updates: Mapping[str, Mapping[str, Any]],
) -> Path:
    """Change some values in the configuration file, keeping the others.

    The file is created if it does not exist. It is written again as a whole:
    its other values and their order are kept, but its comments are lost.
    The new content replaces the old one in a single step,
    so that the file is never left half-written.

    :param path: the YAML file; if None, the default one
    :param updates: the values to change, with the same nested shape as the YAML file
    :return: the file that has been written
    :raises ConfigurationError: if the file cannot be read or written
    """
    target = DEFAULT_CONFIGURATION_FILE_PATH.expanduser() if path is None else path
    content = _read_yaml(target) if target.exists() else {}
    for section, values in updates.items():
        if content.get(section) is None:
            content[section] = {}
        if not isinstance(content[section], dict):
            raise ConfigurationError(f"Section '{section}' must be a mapping")
        content[section].update(values)
    _write_yaml(target, content, sort_keys=False)
    return target


def write_configuration_file(path: Path | None, configuration: Configuration) -> Path:
    """Write the whole configuration to the configuration file, replacing what it contains.

    The new content replaces the old one in a single step,
    so that the file is never left missing or half-written.

    :param path: the YAML file; if None, the default one
    :return: the file that has been written
    :raises ConfigurationError: if the file cannot be written
    """
    target = DEFAULT_CONFIGURATION_FILE_PATH.expanduser() if path is None else path
    _write_yaml(target, configuration.to_dict(), sort_keys=True)
    return target
