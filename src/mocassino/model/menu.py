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
    CLOSE = "close"
    PLAY = "play"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class MenuItem:
    """An item of a menu.

    An item with neither a command nor a submenu only shows information.
    The path is the file or directory to play, for the PLAY command.
    The submenu is a function, so that it is built only when it is opened.
    """

    label: str
    command: MenuCommand | None = None
    path: Path | None = None
    submenu: Callable[[], Menu] | None = None


def _build_shutdown_menu() -> Menu:
    """Build the menu asking to confirm the shutdown; the default choice is to cancel."""
    return Menu(
        title="Shut down?",
        items=(
            MenuItem(label="Cancel", command=MenuCommand.BACK),
            MenuItem(label="Shut down now", command=MenuCommand.SHUTDOWN),
        ),
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


def build_root_menu(library: Library, host: Host) -> Menu:
    """Build the top level menu."""
    return Menu(
        title="Menu",
        items=(
            MenuItem(label="Library", submenu=partial(build_library_menu, library)),
            MenuItem(label="Host", submenu=partial(build_host_menu, host)),
            MenuItem(label="Back to playback", command=MenuCommand.CLOSE),
        ),
    )
