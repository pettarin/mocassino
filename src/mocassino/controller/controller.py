"""The controller: performs the actions asked by the button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from collections.abc import Callable, Mapping

from mocassino.controller.actions import Action, parse_button_map
from mocassino.controller.events import ButtonEvent
from mocassino.model.library import Library
from mocassino.model.menu import (
    Menu,
    MenuCommand,
    build_display_brightness_menu,
    build_display_menu,
    build_display_orientation_menu,
    build_library_menu,
    build_playback_seek_step_menu,
    build_playback_volume_default_menu,
    build_playback_volume_step_menu,
    build_root_menu,
    build_startup_playlist_menu,
    build_startup_state_menu,
    build_startup_volume_menu,
    build_system_moc_state_on_exit_menu,
)
from mocassino.model.moc import MocClient, MocError, MocServerNotRunningError, MocState
from mocassino.model.settings import (
    MocStateOnExit,
    Settings,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.model.state import AppState
from mocassino.model.system import System, SystemShutdownError

LOGGER: logging.Logger = logging.getLogger(__name__)
# For each menu command setting a setting to the value of the selected item:
# the setting, how to get its value from that of the item, and the menu to show again
SETTERS: dict[
    MenuCommand,
    tuple[str, Callable[[str], object], Callable[[Settings], Menu]],
] = {
    MenuCommand.SET_DISPLAY_BRIGHTNESS: (
        "display_brightness",
        int,
        build_display_brightness_menu,
    ),
    MenuCommand.SET_DISPLAY_ORIENTATION: (
        "display_orientation",
        int,
        build_display_orientation_menu,
    ),
    MenuCommand.SET_PLAYBACK_SEEK_STEP: (
        "playback_seek_step",
        int,
        build_playback_seek_step_menu,
    ),
    MenuCommand.SET_PLAYBACK_VOLUME_DEFAULT: (
        "playback_volume_default",
        int,
        build_playback_volume_default_menu,
    ),
    MenuCommand.SET_PLAYBACK_VOLUME_STEP: (
        "playback_volume_step",
        int,
        build_playback_volume_step_menu,
    ),
    MenuCommand.SET_STARTUP_PLAYLIST: (
        "startup_playlist",
        StartupPlaylist,
        build_startup_playlist_menu,
    ),
    MenuCommand.SET_STARTUP_STATE: (
        "startup_state",
        StartupState,
        build_startup_state_menu,
    ),
    MenuCommand.SET_STARTUP_VOLUME: (
        "startup_volume",
        StartupVolume,
        build_startup_volume_menu,
    ),
    MenuCommand.SET_SYSTEM_MOC_STATE_ON_EXIT: (
        "system_moc_state_on_exit",
        MocStateOnExit,
        build_system_moc_state_on_exit_menu,
    ),
}

# For each menu command turning on or off a setting of the display: the setting
TOGGLES: dict[MenuCommand, str] = {
    MenuCommand.TOGGLE_PROGRESS_BAR: "show_progress_bar",
    MenuCommand.TOGGLE_SIDE_ICONS: "show_side_icons",
    MenuCommand.TOGGLE_VOLUME_BAR: "show_volume_bar",
}


class Controller:
    """Performs the actions asked by the button events, on the state, MOC, and the host."""

    def __init__(
        self,
        state: AppState,
        moc: MocClient,
        library: Library,
        system: System,
        button_map: Mapping[str, Mapping[str, str]],
        reset_settings: Callable[[], Settings] | None = None,
        save_settings: Callable[[Settings], None] | None = None,
        switch_display: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize the controller.

        :param button_map: the button map, in plain form
        :param reset_settings: called to make the default settings permanent,
                               returning them; without it, the defaults are the
                               ones of the Settings class, and they are not permanent
        :param save_settings: called with the settings when one of them is changed
                              from the settings menu, to make the change permanent
        :param switch_display: called to turn the display off (False) before the host
                               is rebooted or shut down, and on (True) again if that fails
        :raises ValueError: if the button map is not valid
        """
        self._button_map = parse_button_map(button_map)
        self._handlers: dict[Action, Callable[[], None]] = {
            Action.MENU_BACK: self._menu_back,
            Action.MENU_DOWN: self._menu_down,
            Action.MENU_SELECT: self._menu_select,
            Action.MENU_UP: self._menu_up,
            Action.NEXT: self._next,
            Action.OPEN_MENU: self._open_menu,
            Action.PLAY_PAUSE: self._play_pause,
            Action.PREVIOUS: self._previous,
            Action.SEEK_BACKWARD: self._seek_backward,
            Action.SEEK_FORWARD: self._seek_forward,
            Action.VOLUME_DOWN: self._volume_down,
            Action.VOLUME_UP: self._volume_up,
        }
        self._library = library
        self._moc = moc
        self._reset_settings = reset_settings
        self._save_settings = save_settings
        self._state = state
        self._switch_display = switch_display
        self._system = system

    def _change_volume(self, delta: int) -> None:
        """Change the volume by the given amount."""
        self._moc.set_volume(self._state.change_volume(delta))

    def _halt(self, halt: Callable[[], None]) -> None:
        """Reboot or shut down the host, with the display turned off.

        The display is turned off first, as the host leaves it as it is when it halts.
        If the host cannot be rebooted or shut down, the display is turned on again,
        and the player carries on.

        :param halt: the method of the system rebooting or shutting down the host
        :raises SystemShutdownError: if the host cannot be rebooted or shut down
        """
        self._state.close_menus()
        self._state.shutting_down = True
        if self._switch_display is not None:
            self._switch_display(False)
        try:
            halt()
        except SystemShutdownError:
            self._state.shutting_down = False
            if self._switch_display is not None:
                self._switch_display(True)
            raise

    def _menu_back(self) -> None:
        """Go back one level, to the previous menu or to playback mode."""
        self._state.pop_menu()

    def _menu_down(self) -> None:
        """Select the next item of the current menu."""
        self._move_selection(1)

    def _menu_select(self) -> None:
        """Open the submenu of the selected item, or perform its command."""
        menu = self._state.current_menu
        item = menu.selected if menu is not None else None
        if item is None:
            return
        if item.submenu is not None:
            self._state.open_menu(item.submenu())
        elif item.command is MenuCommand.BACK:
            self._state.pop_menu()
        elif item.command is MenuCommand.PLAY and item.path is not None:
            self._state.close_menus()
            self._moc.play(item.path)
            self._state.played_path = str(item.path)
        elif item.command in SETTERS and item.value is not None:
            attribute, convert, build_menu = SETTERS[item.command]
            settings = self._state.settings
            setattr(settings, attribute, convert(item.value))
            self._state.replace_menu(build_menu(settings))
            if self._save_settings is not None:
                self._save_settings(settings)
        elif item.command is MenuCommand.REBOOT:
            self._halt(self._system.reboot)
        elif item.command is MenuCommand.RESET_SETTINGS:
            self._reset()
        elif item.command is MenuCommand.SHUTDOWN:
            self._halt(self._system.shutdown)
        elif item.command in TOGGLES:
            settings = self._state.settings
            attribute = TOGGLES[item.command]
            setattr(settings, attribute, not getattr(settings, attribute))
            self._state.replace_menu(build_display_menu(settings))
            if self._save_settings is not None:
                self._save_settings(settings)

    def _menu_up(self) -> None:
        """Select the previous item of the current menu."""
        self._move_selection(-1)

    def _move_selection(self, delta: int) -> None:
        """Move the selection of the current menu, if any."""
        menu = self._state.current_menu
        if menu is not None:
            menu.move(delta)

    def _next(self) -> None:
        """Play the next track."""
        self._moc.next()

    def _open_menu(self) -> None:
        """Show the top level menu."""
        self._state.close_menus()
        self._state.open_menu(build_root_menu(self._library, self._system, self._state.settings))

    def _play_pause(self) -> None:
        """Toggle between playing and paused; if stopped, play the playlist."""
        if self._state.status.state is MocState.STOP:
            self._moc.play_playlist()
        else:
            self._moc.toggle_pause()

    def _previous(self) -> None:
        """Play the previous track."""
        self._moc.previous()

    def _reset(self) -> None:
        """Reset the settings to the defaults, at once, and go back from the confirmation."""
        defaults = Settings() if self._reset_settings is None else self._reset_settings()
        self._state.settings.update(defaults)
        self._state.pop_menu()

    def _seek_backward(self) -> None:
        """Seek backward in the current track."""
        self._moc.seek(-self._state.settings.playback_seek_step)

    def _seek_forward(self) -> None:
        """Seek forward in the current track."""
        self._moc.seek(self._state.settings.playback_seek_step)

    def _volume_down(self) -> None:
        """Turn the volume down."""
        self._change_volume(-self._state.settings.playback_volume_step)

    def _volume_up(self) -> None:
        """Turn the volume up."""
        self._change_volume(self._state.settings.playback_volume_step)

    def choose_folder(self) -> None:
        """Show the menu of the library, on top of the top level menu, to choose what to play."""
        self._open_menu()
        self._state.open_menu(build_library_menu(self._library))

    def handle(self, event: ButtonEvent) -> None:
        """Perform the action associated to the given event in the current mode, if any.

        If what is shown on the display is rotated, the buttons are taken for those
        at the same corners of what is shown.
        The errors of MOC and of the host are logged, not raised;
        if the MOC server is not running, it is started.
        """
        event = event.rotated(self._state.settings.display_orientation)
        action = self._button_map.get((self._state.mode, event))
        if action is None:
            return
        LOGGER.debug("%s in %s mode: %s", event, self._state.mode, action)
        try:
            try:
                self._handlers[action]()
            except MocServerNotRunningError:
                LOGGER.warning("The MOC server is not running: starting it")
                self._moc.start_server()
        except (SystemShutdownError, MocError) as exc:
            LOGGER.error("Cannot perform %s: %s", action, exc)
