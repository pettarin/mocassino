"""The controller: performs the actions asked by the button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from collections.abc import Callable, Mapping

from mocassino.controller.actions import Action, parse_button_map
from mocassino.controller.events import ButtonEvent
from mocassino.model.host import Host, HostError
from mocassino.model.library import Library
from mocassino.model.menu import MenuCommand, build_root_menu
from mocassino.model.moc import MocClient, MocError, MocServerNotRunningError, MocState
from mocassino.model.state import AppState

LOGGER: logging.Logger = logging.getLogger(__name__)


class Controller:
    """Performs the actions asked by the button events, on the state, MOC, and the host."""

    def __init__(
        self,
        state: AppState,
        moc: MocClient,
        library: Library,
        host: Host,
        button_map: Mapping[str, Mapping[str, str]],
        volume_step: int,
    ) -> None:
        """Initialize the controller.

        :param button_map: the button map, in plain form
        :param volume_step: the amount of each volume change
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
            Action.VOLUME_DOWN: self._volume_down,
            Action.VOLUME_UP: self._volume_up,
        }
        self._host = host
        self._library = library
        self._moc = moc
        self._state = state
        self._volume_step = volume_step

    def _change_volume(self, delta: int) -> None:
        """Change the volume by the given amount."""
        self._moc.set_volume(self._state.change_volume(delta))

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
        elif item.command is MenuCommand.CLOSE:
            self._state.close_menus()
        elif item.command is MenuCommand.PLAY and item.path is not None:
            self._state.close_menus()
            self._moc.play(item.path)
        elif item.command is MenuCommand.SHUTDOWN:
            self._state.close_menus()
            self._host.shutdown()

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
        self._state.open_menu(build_root_menu(self._library, self._host))

    def _play_pause(self) -> None:
        """Toggle between playing and paused; if stopped, play the playlist."""
        if self._state.status.state is MocState.STOP:
            self._moc.play_playlist()
        else:
            self._moc.toggle_pause()

    def _previous(self) -> None:
        """Play the previous track."""
        self._moc.previous()

    def _volume_down(self) -> None:
        """Turn the volume down."""
        self._change_volume(-self._volume_step)

    def _volume_up(self) -> None:
        """Turn the volume up."""
        self._change_volume(self._volume_step)

    def handle(self, event: ButtonEvent) -> None:
        """Perform the action associated to the given event in the current mode, if any.

        The errors of MOC and of the host are logged, not raised;
        if the MOC server is not running, it is started.
        """
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
        except (HostError, MocError) as exc:
            LOGGER.error("Cannot perform %s: %s", action, exc)
