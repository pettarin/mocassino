"""The menus: plain data describing what can be selected, built lazily level by level.

Selecting an item either opens its submenu or asks for a command;
the commands are executed by the controller, not here.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path

from mocassino.model.host import Host
from mocassino.model.library import Library
from mocassino.model.settings import (
    ORIENTATIONS,
    Settings,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)

# The seek steps, in seconds, the default volumes, and the volume steps
# that can be chosen from the menu
SEEK_STEP_CHOICES: tuple[int, ...] = (1, 2, 5, 10, 30, 60)
VOLUME_DEFAULT_CHOICES: tuple[int, ...] = tuple(range(0, 101, 5))
VOLUME_STEP_CHOICES: tuple[int, ...] = (1, 2, 4, 5, 10)


@dataclass
class Menu:
    """A list of items, one of which is selected."""

    title: str
    items: tuple[MenuItem, ...]
    selected_index: int = 0

    def move(self, delta: int) -> None:
        """Move the selection by the given number of items, wrapping around."""
        if self.items:
            self.selected_index = (self.selected_index + delta) % len(self.items)

    @property
    def selected(self) -> MenuItem | None:
        """The selected item, or None if the menu is empty."""
        return self.items[self.selected_index] if self.items else None


class MenuCommand(StrEnum):
    """What the controller is asked to do when an item is selected."""

    BACK = "back"
    PLAY = "play"
    SET_DISPLAY_ORIENTATION = "set_display_orientation"
    SET_PLAYBACK_SEEK_STEP = "set_playback_seek_step"
    SET_PLAYBACK_VOLUME_DEFAULT = "set_playback_volume_default"
    SET_PLAYBACK_VOLUME_STEP = "set_playback_volume_step"
    SET_STARTUP_PLAYLIST = "set_startup_playlist"
    SET_STARTUP_STATE = "set_startup_state"
    SET_STARTUP_VOLUME = "set_startup_volume"
    SHUTDOWN = "shutdown"
    TOGGLE_PROGRESS_BAR = "toggle_progress_bar"
    TOGGLE_SIDE_ICONS = "toggle_side_icons"
    TOGGLE_VOLUME_BAR = "toggle_volume_bar"


@dataclass(frozen=True)
class MenuItem:
    """An item of a menu.

    An item with neither a command nor a submenu only shows information.
    An item standing for a setting that is either on or off says which, as checked;
    the other items leave it to None.
    The path is the file or directory to play, for the PLAY command.
    The value is what a setting is set to, for the commands setting one.
    The submenu is a function, so that it is built only when it is opened.
    """

    label: str
    checked: bool | None = None
    command: MenuCommand | None = None
    path: Path | None = None
    submenu: Callable[[], Menu] | None = None
    value: str | None = None


def _build_choice_menu(
    title: str,
    choices: tuple[StrEnum, ...],
    current: StrEnum,
    command: MenuCommand,
) -> Menu:
    """Build a menu choosing one of the values of a setting.

    The choices are in the given order, which is the alphabetical order of the values.
    Each is labelled with its value, with spaces for the underscores and a capital first letter.
    The current choice is the checked one, and it is the selected item too.
    """
    return Menu(
        title=title,
        items=tuple(
            MenuItem(
                label=choice.value.replace("_", " ").capitalize(),
                checked=choice is current,
                command=command,
                value=choice.value,
            )
            for choice in choices
        ),
        selected_index=choices.index(current),
    )


def _build_number_menu(
    title: str,
    choices: tuple[int, ...],
    current: int,
    command: MenuCommand,
) -> Menu:
    """Build a menu choosing one of some numbers as the value of a setting.

    The current value is the checked one, if it is one of the choices;
    the selected item is the choice closest to it.
    """
    return Menu(
        title=title,
        items=tuple(
            MenuItem(
                label=str(choice),
                checked=choice == current,
                command=command,
                value=str(choice),
            )
            for choice in choices
        ),
        selected_index=min(range(len(choices)), key=lambda index: abs(choices[index] - current)),
    )


def _build_shutdown_menu() -> Menu:
    """Build the menu asking to confirm the shutdown; the default choice is to cancel."""
    return Menu(
        title="Shut down?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Shut down now", command=MenuCommand.SHUTDOWN),
        ),
    )


def build_display_menu(settings: Settings) -> Menu:
    """Build the menu showing the settings of the display, and changing them.

    Like the startup menu, it has to be built again when a setting changes.
    """
    return Menu(
        title="Display",
        items=(
            MenuItem(
                label="Orientation",
                submenu=partial(build_display_orientation_menu, settings),
            ),
            MenuItem(
                label="Show progress bar",
                checked=settings.show_progress_bar,
                command=MenuCommand.TOGGLE_PROGRESS_BAR,
            ),
            MenuItem(
                label="Show side icons",
                checked=settings.show_side_icons,
                command=MenuCommand.TOGGLE_SIDE_ICONS,
            ),
            MenuItem(
                label="Show volume bar",
                checked=settings.show_volume_bar,
                command=MenuCommand.TOGGLE_VOLUME_BAR,
            ),
        ),
    )


def build_display_orientation_menu(settings: Settings) -> Menu:
    """Build the menu choosing by how many degrees what is shown on the display is rotated.

    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Orientation",
        ORIENTATIONS,
        settings.display_orientation,
        MenuCommand.SET_DISPLAY_ORIENTATION,
    )


def build_host_menu(host: Host) -> Menu:
    """Build the menu showing the name and the IP address of the host, and shutting it down."""
    return Menu(
        title="Host",
        items=(
            MenuItem(label=f"Name: {host.hostname()}"),
            MenuItem(label=f"IP: {host.ip_address() or 'not available'}"),
            MenuItem(label="Shut down", submenu=_build_shutdown_menu),
        ),
    )


def build_library_menu(library: Library, directory_path: Path | None = None) -> Menu:
    """Build the menu of a directory of the library.

    :param directory_path: the directory; if None, the music root directory
    """
    directory_path = directory_path or library.directory_path
    is_root = directory_path == library.directory_path
    entries = library.list_entries(directory_path)
    items: list[MenuItem] = []
    if entries:
        items.append(
            MenuItem(label="Play this folder", command=MenuCommand.PLAY, path=directory_path)
        )
    else:
        items.append(MenuItem(label="(empty)"))
    for entry in entries:
        if entry.is_directory:
            submenu = partial(build_library_menu, library, entry.path)
            items.append(MenuItem(label=entry.name, submenu=submenu))
        else:
            items.append(MenuItem(label=entry.name, command=MenuCommand.PLAY, path=entry.path))
    return Menu(title="Library" if is_root else directory_path.name, items=tuple(items))


def build_playback_menu(settings: Settings) -> Menu:
    """Build the menu leading to the settings of the playback.

    They are the seek step, the default volume, and the volume step.
    """
    return Menu(
        title="Playback",
        items=(
            MenuItem(
                label="Seek step (s)",
                submenu=partial(build_playback_seek_step_menu, settings),
            ),
            MenuItem(
                label="Volume default (%)",
                submenu=partial(build_playback_volume_default_menu, settings),
            ),
            MenuItem(
                label="Volume step (%)",
                submenu=partial(build_playback_volume_step_menu, settings),
            ),
        ),
    )


def build_playback_seek_step_menu(settings: Settings) -> Menu:
    """Build the menu choosing the amount of each seek, in seconds.

    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Seek step (s)",
        SEEK_STEP_CHOICES,
        settings.playback_seek_step,
        MenuCommand.SET_PLAYBACK_SEEK_STEP,
    )


def build_playback_volume_default_menu(settings: Settings) -> Menu:
    """Build the menu choosing the default volume, which the service can set when it starts.

    It has to be built again when the volume changes.
    """
    return _build_number_menu(
        "Volume default (%)",
        VOLUME_DEFAULT_CHOICES,
        settings.playback_volume_default,
        MenuCommand.SET_PLAYBACK_VOLUME_DEFAULT,
    )


def build_playback_volume_step_menu(settings: Settings) -> Menu:
    """Build the menu choosing the amount of each volume change.

    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Volume step (%)",
        VOLUME_STEP_CHOICES,
        settings.playback_volume_step,
        MenuCommand.SET_PLAYBACK_VOLUME_STEP,
    )


def build_root_menu(library: Library, host: Host, settings: Settings) -> Menu:
    """Build the top level menu."""
    return Menu(
        title="Menu",
        items=(
            MenuItem(label="Library", submenu=partial(build_library_menu, library)),
            MenuItem(label="Settings", submenu=partial(build_settings_menu, settings)),
            MenuItem(label="Host", submenu=partial(build_host_menu, host)),
        ),
    )


def build_settings_menu(settings: Settings) -> Menu:
    """Build the menu leading to the settings, grouped by what they are about."""
    return Menu(
        title="Settings",
        items=(
            MenuItem(label="Display", submenu=partial(build_display_menu, settings)),
            MenuItem(label="Playback", submenu=partial(build_playback_menu, settings)),
            MenuItem(label="Startup", submenu=partial(build_startup_menu, settings)),
        ),
    )


def build_startup_menu(settings: Settings) -> Menu:
    """Build the menu leading to the settings of what happens at startup."""
    return Menu(
        title="Startup",
        items=(
            MenuItem(label="Playlist", submenu=partial(build_startup_playlist_menu, settings)),
            MenuItem(label="State", submenu=partial(build_startup_state_menu, settings)),
            MenuItem(label="Volume", submenu=partial(build_startup_volume_menu, settings)),
        ),
    )


def build_startup_playlist_menu(settings: Settings) -> Menu:
    """Build the menu choosing what the service does about the playlist when it starts.

    It has to be built again when the choice changes.
    """
    return _build_choice_menu(
        "Playlist",
        tuple(StartupPlaylist),
        settings.startup_playlist,
        MenuCommand.SET_STARTUP_PLAYLIST,
    )


def build_startup_state_menu(settings: Settings) -> Menu:
    """Build the menu choosing what playback state the service sets when it starts.

    It has to be built again when the choice changes.
    """
    return _build_choice_menu(
        "State",
        tuple(StartupState),
        settings.startup_state,
        MenuCommand.SET_STARTUP_STATE,
    )


def build_startup_volume_menu(settings: Settings) -> Menu:
    """Build the menu choosing what volume the service sets when it starts.

    It has to be built again when the choice changes.
    """
    return _build_choice_menu(
        "Volume",
        tuple(StartupVolume),
        settings.startup_volume,
        MenuCommand.SET_STARTUP_VOLUME,
    )
