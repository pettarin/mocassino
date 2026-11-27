"""The menus: plain data describing what can be selected, built lazily level by level.

Selecting an item either opens its submenu or asks for a command;
the commands are executed by the controller, not here.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path

from mocassino.constants import (
    DISPLAY_TIMEOUT_CHOICES,
    ORIENTATIONS,
    REFRESH_DELAY_CHOICES,
    VOLUME_MAX,
    VOLUME_MIN,
    MocStateOnExit,
    RightTimerValue,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.model.colors import COLOR_NAMES, COLOR_ROLES, color_name
from mocassino.model.library import Library, list_directories
from mocassino.model.settings import Settings
from mocassino.model.system import System

# The words written in capitals in the labels of the choices
ACRONYMS: dict[str, str] = {"moc": "MOC"}
# The brightnesses of the display, the seek steps, in seconds, the default volumes,
# and the volume steps that can be chosen from the menu, all but the seek steps in percent
BRIGHTNESS_CHOICES: tuple[int, ...] = tuple(range(0, 101, 5))
# What follows the label of the current color in the menus choosing a color
CURRENT_MARK: str = "[X]"
SEEK_STEP_CHOICES: tuple[int, ...] = (1, 2, 5, 10, 30, 60)
VOLUME_DEFAULT_CHOICES: tuple[int, ...] = tuple(range(VOLUME_MIN, VOLUME_MAX + 1, 5))
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
    CHOOSE_LIBRARY_DIRECTORY = "choose_library_directory"
    CONFIRM_RUN_SAVE_STATE_ON_REFRESH = "confirm_run_save_state_on_refresh"
    PLAY = "play"
    REBOOT = "reboot"
    RESET_ALL_COLORS = "reset_all_colors"
    RESET_ALL_SETTINGS = "reset_all_settings"
    RESTART_SERVICE = "restart_service"
    SET_DISPLAY_BRIGHTNESS = "set_display_brightness"
    SET_DISPLAY_COLORS_ACCENTED = "set_display_colors_accented"
    SET_DISPLAY_COLORS_BACKGROUND = "set_display_colors_background"
    SET_DISPLAY_COLORS_MUTED = "set_display_colors_muted"
    SET_DISPLAY_COLORS_NORMAL = "set_display_colors_normal"
    SET_DISPLAY_COLORS_TRACK = "set_display_colors_track"
    SET_DISPLAY_ORIENTATION = "set_display_orientation"
    SET_DISPLAY_TIMEOUT = "set_display_timeout"
    SET_LIBRARY_DIRECTORY = "set_library_directory"
    SET_PLAYBACK_SEEK_STEP = "set_playback_seek_step"
    SET_PLAYBACK_VOLUME_DEFAULT = "set_playback_volume_default"
    SET_PLAYBACK_VOLUME_STEP = "set_playback_volume_step"
    SET_RIGHT_TIMER_VALUE = "set_right_timer_value"
    SET_RUN_MOC_STATE_ON_EXIT = "set_run_moc_state_on_exit"
    SET_RUN_REFRESH_DELAY = "set_run_refresh_delay"
    SET_STARTUP_PLAYLIST = "set_startup_playlist"
    SET_STARTUP_STATE = "set_startup_state"
    SET_STARTUP_VOLUME = "set_startup_volume"
    SHUTDOWN = "shutdown"
    TOGGLE_PLAYLIST_BAR = "toggle_playlist_bar"
    TOGGLE_PROGRESS_BAR = "toggle_progress_bar"
    TOGGLE_RUN_SAVE_STATE_ON_EXIT = "toggle_run_save_state_on_exit"
    TOGGLE_RUN_SAVE_STATE_ON_REFRESH = "toggle_run_save_state_on_refresh"
    TOGGLE_RUN_SAVE_STATE_ON_STARTUP = "toggle_run_save_state_on_startup"
    TOGGLE_RUN_SAVE_STATE_ON_STATE_CHANGE = "toggle_run_save_state_on_state_change"
    TOGGLE_RUN_SAVE_STATE_ON_TRACK_CHANGE = "toggle_run_save_state_on_track_change"
    TOGGLE_RUN_SAVE_STATE_ON_VOLUME_CHANGE = "toggle_run_save_state_on_volume_change"
    TOGGLE_SIDE_ICONS = "toggle_side_icons"
    TOGGLE_TIMERS = "toggle_timers"
    TOGGLE_VOLUME_BAR = "toggle_volume_bar"


@dataclass(frozen=True)
class MenuItem:
    """An item of a menu.

    An item with neither a command nor a submenu only shows information.
    An item standing for a setting that is either on or off says which, as checked;
    the other items leave it to None.
    An item standing for a color has it, as a name or an HTML code, to show it.
    The path is the file or directory to play, for the PLAY command,
    or the directory to use as the music root directory, for the SET_LIBRARY_DIRECTORY command.
    The value is what a setting is set to, for the commands setting one.
    The submenu is a function, so that it is built only when it is opened.
    """

    label: str
    checked: bool | None = None
    color: str | None = None
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
    Each is labelled with its value: see _label.
    The current choice is the checked one, and it is the selected item too.
    """
    return Menu(
        title=title,
        items=tuple(
            MenuItem(
                label=_label(choice.value),
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
    choices: tuple[float, ...],
    current: float,
    command: MenuCommand,
    labels: Mapping[float, str] | None = None,
) -> Menu:
    """Build a menu choosing one of some numbers as the value of a setting.

    Each choice is labelled with its number, unless the labels give another label for it.
    The current value is the checked one, if it is one of the choices;
    the selected item is the choice closest to it.
    """
    labels = labels or {}
    return Menu(
        title=title,
        items=tuple(
            MenuItem(
                label=labels.get(choice, str(choice)),
                checked=choice == current,
                command=command,
                value=str(choice),
            )
            for choice in choices
        ),
        selected_index=min(range(len(choices)), key=lambda index: abs(choices[index] - current)),
    )


def _build_reboot_menu() -> Menu:
    """Build the menu asking to confirm the reboot; the default choice is to cancel."""
    return Menu(
        title="Reboot?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Reboot now", command=MenuCommand.REBOOT),
        ),
    )


def _build_reset_all_colors_menu() -> Menu:
    """Build the menu asking to confirm the reset of the colors; the default is to cancel."""
    return Menu(
        title="Reset all colors?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Reset now", command=MenuCommand.RESET_ALL_COLORS),
        ),
    )


def _build_reset_all_settings_menu() -> Menu:
    """Build the menu asking to confirm the reset of the settings; the default is to cancel."""
    return Menu(
        title="Reset all settings?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Reset now", command=MenuCommand.RESET_ALL_SETTINGS),
        ),
    )


def _build_restart_service_menu() -> Menu:
    """Build the menu asking to confirm the restart of the service; the default is to cancel."""
    return Menu(
        title="Restart service?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Restart now", command=MenuCommand.RESTART_SERVICE),
        ),
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


def _label(value: str) -> str:
    """Return the label of a value of a setting, e.g., "Use MOC state" for "use_moc_state".

    The words are separated by spaces instead of underscores, the first one has
    a capital first letter, and the acronyms are written in capitals.
    """
    words = [ACRONYMS.get(word, word) for word in value.split("_")]
    words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words)


def build_confirm_run_save_state_on_refresh_menu() -> Menu:
    """Build the menu asking to confirm that the state is saved at every refresh.

    It is asked as the state file is then written about once a second during the playback,
    which may wear out an SD card. The menu first says so, on three rows that only show
    information, so that each fits the width of the display; the default choice is to cancel.
    """
    return Menu(
        title="Save on refresh?",
        items=(
            MenuItem(label="Enabling this will write"),
            MenuItem(label="to disk/card a lot and"),
            MenuItem(label="it is not recommended."),
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Confirm", command=MenuCommand.CONFIRM_RUN_SAVE_STATE_ON_REFRESH),
        ),
        selected_index=3,
    )


def build_display_brightness_menu(settings: Settings) -> Menu:
    """Build the menu choosing the brightness of the display, in percent.

    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Brightness (%)",
        BRIGHTNESS_CHOICES,
        settings.display_brightness,
        MenuCommand.SET_DISPLAY_BRIGHTNESS,
    )


def build_display_color_menu(settings: Settings, role: str) -> Menu:
    """Build the menu choosing the color of the given role, among the named ones.

    The current color has [X] after its name, and it is the selected item.
    A current color with no name (an HTML code) is shown first, without a command.
    It has to be built again when the choice changes.

    :param role: the role of the color, e.g., "accented"
    """
    current = getattr(settings, f"display_colors_{role}")
    name = color_name(current)
    command = MenuCommand(f"set_display_colors_{role}")
    items: list[MenuItem] = []
    if name is None:
        items.append(MenuItem(label=f"{current} {CURRENT_MARK}", color=current))
    for candidate in COLOR_NAMES:
        items.append(
            MenuItem(
                label=f"{candidate} {CURRENT_MARK}" if candidate == name else candidate,
                color=candidate,
                command=command,
                value=candidate,
            )
        )
    selected_index = 0 if name is None else COLOR_NAMES.index(name)
    return Menu(title=role.capitalize(), items=tuple(items), selected_index=selected_index)


def build_display_colors_menu(settings: Settings) -> Menu:
    """Build the menu leading to the menus choosing the colors of the display, one per role.

    It also resets the colors to the default ones, after a confirmation.
    """
    items = [
        MenuItem(
            label=role.capitalize(),
            submenu=partial(build_display_color_menu, settings, role),
        )
        for role in COLOR_ROLES
    ]
    items.append(MenuItem(label="Reset all colors", submenu=_build_reset_all_colors_menu))
    return Menu(title="Colors", items=tuple(items))


def build_display_menu(settings: Settings) -> Menu:
    """Build the menu showing the settings of the display, and changing them.

    Like the startup menu, it has to be built again when a setting changes.
    """
    return Menu(
        title="Display",
        items=(
            MenuItem(
                label="Brightness (%)",
                submenu=partial(build_display_brightness_menu, settings),
            ),
            MenuItem(
                label="Colors",
                submenu=partial(build_display_colors_menu, settings),
            ),
            MenuItem(
                label="Orientation",
                submenu=partial(build_display_orientation_menu, settings),
            ),
            MenuItem(
                label="Timeout (s)",
                submenu=partial(build_display_timeout_menu, settings),
            ),
            MenuItem(
                label="UI elements",
                submenu=partial(build_display_ui_elements_menu, settings),
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


def build_display_right_timer_value_menu(settings: Settings) -> Menu:
    """Build the menu choosing what the timer on the right shows in playback mode.

    It has to be built again when the choice changes.
    """
    return _build_choice_menu(
        "Right timer value",
        tuple(RightTimerValue),
        settings.right_timer_value,
        MenuCommand.SET_RIGHT_TIMER_VALUE,
    )


def build_display_timeout_menu(settings: Settings) -> Menu:
    """Build the menu choosing after how many seconds without a button press the display is off.

    The choice 0, which keeps the display on, is labelled "No timeout".
    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Timeout (s)",
        DISPLAY_TIMEOUT_CHOICES,
        settings.display_timeout,
        MenuCommand.SET_DISPLAY_TIMEOUT,
        labels={0: "No timeout"},
    )


def build_display_ui_elements_menu(settings: Settings) -> Menu:
    """Build the menu showing which elements are shown in playback mode, and changing them.

    Like the display menu, it has to be built again when a setting changes.
    """
    return Menu(
        title="UI elements",
        items=(
            MenuItem(
                label="Right timer value",
                submenu=partial(build_display_right_timer_value_menu, settings),
            ),
            MenuItem(
                label="Show playlist bar",
                checked=settings.show_playlist_bar,
                command=MenuCommand.TOGGLE_PLAYLIST_BAR,
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
                label="Show timers",
                checked=settings.show_timers,
                command=MenuCommand.TOGGLE_TIMERS,
            ),
            MenuItem(
                label="Show volume bar",
                checked=settings.show_volume_bar,
                command=MenuCommand.TOGGLE_VOLUME_BAR,
            ),
        ),
    )


def build_information_menu(system: System) -> Menu:
    """Build the menu showing information about the host: its name and its IP address."""
    return Menu(
        title="Information",
        items=(
            MenuItem(label=f"Name: {system.hostname()}"),
            MenuItem(label=f"IP: {system.ip_address() or 'not available'}"),
        ),
    )


def build_library_directory_menu(directory_path: Path, selected_path: Path | None = None) -> Menu:
    """Build the menu of a directory of the host, to choose the music root directory.

    The directory can be chosen, or one of its subdirectories can be opened.

    :param directory_path: the directory, which can be anywhere on the host
    :param selected_path: the subdirectory to select, if it is listed;
                          otherwise, the first item is selected
    """
    directories = list_directories(directory_path)
    items = [
        MenuItem(
            label="Use this folder",
            command=MenuCommand.SET_LIBRARY_DIRECTORY,
            path=directory_path,
        )
    ]
    if not directories:
        items.append(MenuItem(label="(no folders)"))
    for directory in directories:
        submenu = partial(build_library_directory_menu, directory)
        items.append(MenuItem(label=directory.name, submenu=submenu))
    selected_index = 0
    if selected_path in directories:
        selected_index = directories.index(selected_path) + 1
    return Menu(
        title=directory_path.name or str(directory_path),
        items=tuple(items),
        selected_index=selected_index,
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


def build_root_menu(library: Library, system: System, settings: Settings) -> Menu:
    """Build the top level menu."""
    return Menu(
        title="Menu",
        items=(
            MenuItem(label="Library", submenu=partial(build_library_menu, library)),
            MenuItem(label="Settings", submenu=partial(build_settings_menu, settings)),
            MenuItem(label="System", submenu=partial(build_system_menu, system)),
            MenuItem(label="Information", submenu=partial(build_information_menu, system)),
        ),
    )


def build_run_menu(settings: Settings) -> Menu:
    """Build the menu leading to the settings of how the service is run.

    That is: the music root directory, what is done to MOC on exit,
    how long the main loop waits before each refresh, and when the state is saved.
    """
    return Menu(
        title="Run",
        items=(
            MenuItem(label="Library directory", command=MenuCommand.CHOOSE_LIBRARY_DIRECTORY),
            MenuItem(
                label="MOC state on exit",
                submenu=partial(build_run_moc_state_on_exit_menu, settings),
            ),
            MenuItem(
                label="Refresh delay (s)",
                submenu=partial(build_run_refresh_delay_menu, settings),
            ),
            MenuItem(label="Save state", submenu=partial(build_run_save_state_menu, settings)),
        ),
    )


def build_run_moc_state_on_exit_menu(settings: Settings) -> Menu:
    """Build the menu choosing what the service does to MOC when it exits.

    It has to be built again when the choice changes.
    """
    return _build_choice_menu(
        "MOC state on exit",
        tuple(MocStateOnExit),
        settings.run_moc_state_on_exit,
        MenuCommand.SET_RUN_MOC_STATE_ON_EXIT,
    )


def build_run_refresh_delay_menu(settings: Settings) -> Menu:
    """Build the menu choosing how long the main loop waits for a button event before a refresh.

    It has to be built again when the choice changes.
    """
    return _build_number_menu(
        "Refresh delay (s)",
        REFRESH_DELAY_CHOICES,
        settings.run_refresh_delay,
        MenuCommand.SET_RUN_REFRESH_DELAY,
    )


def build_run_save_state_menu(settings: Settings) -> Menu:
    """Build the menu showing when the state is saved to the state file, and changing it.

    Like the display menu, it has to be built again when a setting changes.
    """
    return Menu(
        title="Save state",
        items=(
            MenuItem(
                label="On exit",
                checked=settings.run_save_state_on_exit,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_EXIT,
            ),
            MenuItem(
                label="On refresh",
                checked=settings.run_save_state_on_refresh,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_REFRESH,
            ),
            MenuItem(
                label="On startup",
                checked=settings.run_save_state_on_startup,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_STARTUP,
            ),
            MenuItem(
                label="On state change",
                checked=settings.run_save_state_on_state_change,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_STATE_CHANGE,
            ),
            MenuItem(
                label="On track change",
                checked=settings.run_save_state_on_track_change,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_TRACK_CHANGE,
            ),
            MenuItem(
                label="On volume change",
                checked=settings.run_save_state_on_volume_change,
                command=MenuCommand.TOGGLE_RUN_SAVE_STATE_ON_VOLUME_CHANGE,
            ),
        ),
    )


def build_settings_menu(settings: Settings) -> Menu:
    """Build the menu leading to the settings, grouped by what they are about.

    It also resets all the settings, after a confirmation.
    """
    return Menu(
        title="Settings",
        items=(
            MenuItem(label="Display", submenu=partial(build_display_menu, settings)),
            MenuItem(label="Playback", submenu=partial(build_playback_menu, settings)),
            MenuItem(label="Run", submenu=partial(build_run_menu, settings)),
            MenuItem(label="Startup", submenu=partial(build_startup_menu, settings)),
            MenuItem(label="Reset all settings", submenu=_build_reset_all_settings_menu),
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


def build_system_menu(system: System) -> Menu:
    """Build the menu restarting the service, and rebooting or shutting down the host.

    Each of them is done after a confirmation.
    """
    return Menu(
        title="System",
        items=(
            MenuItem(label="Restart service", submenu=_build_restart_service_menu),
            MenuItem(label="Reboot", submenu=_build_reboot_menu),
            MenuItem(label="Shut down", submenu=_build_shutdown_menu),
        ),
    )
