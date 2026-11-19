"""The state of the application: what the view draws and the controller changes.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from mocassino.model.menu import Menu
from mocassino.model.moc import MocStatus
from mocassino.model.settings import Settings


@dataclass
class AppState:
    """The state of the application.

    The menus are a stack: the last one is the menu being shown,
    and the application is in playback mode when the stack is empty.

    The played path is what MOC was last given to play (a directory, or a single file),
    if known. The playlist is the tracks of what the current track is played from,
    in the order MOC plays them (see the playlist module).
    The host is shutting down once its reboot or its shutdown has been asked from the menu.
    """

    menus: list[Menu] = field(default_factory=list)
    played_path: str | None = None
    playlist: tuple[str, ...] = ()
    settings: Settings = field(default_factory=Settings)
    shutting_down: bool = False
    status: MocStatus = field(default_factory=MocStatus)
    volume: int = 50

    def change_volume(self, delta: int) -> int:
        """Change the volume by the given amount, within 0 and 100, and return it."""
        self.volume = max(0, min(100, self.volume + delta))
        return self.volume

    def close_menus(self) -> None:
        """Close all the menus, going back to playback mode."""
        self.menus.clear()

    @property
    def current_menu(self) -> Menu | None:
        """The menu being shown, or None in playback mode."""
        return self.menus[-1] if self.menus else None

    @property
    def mode(self) -> Mode:
        """The mode of the application."""
        return Mode.MENU if self.menus else Mode.PLAYBACK

    def open_menu(self, menu: Menu) -> None:
        """Show the given menu, on top of the current one, if any."""
        self.menus.append(menu)

    def pop_menu(self) -> None:
        """Go back one level, to the previous menu or to playback mode."""
        if self.menus:
            self.menus.pop()

    def replace_menu(self, menu: Menu) -> None:
        """Show the given menu in place of the current one, keeping the selection in place.

        If no menu is shown, the given one is shown as the first.
        """
        if self.menus:
            last_index = max(0, len(menu.items) - 1)
            menu.selected_index = min(self.menus[-1].selected_index, last_index)
            self.menus[-1] = menu
        else:
            self.menus.append(menu)


class Mode(StrEnum):
    """The mode of the application."""

    MENU = "menu"
    PLAYBACK = "playback"
