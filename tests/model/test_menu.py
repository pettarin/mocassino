"""Tests for the menus.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.model.host import Host
from mocassino.model.library import Library
from mocassino.model.menu import (
    Menu,
    MenuCommand,
    MenuItem,
    build_host_menu,
    build_library_menu,
    build_root_menu,
    build_settings_menu,
)
from mocassino.model.settings import Settings


@pytest.fixture
def host(mocker):
    host = mocker.create_autospec(Host, instance=True)
    host.hostname.return_value = "pirate"
    host.ip_address.return_value = "192.168.1.20"
    return host


@pytest.fixture
def library(tmp_path):
    """Create a library with an album, an empty directory, and a loose track."""
    root = tmp_path / "music"
    (root / "Artist" / "Album").mkdir(parents=True)
    (root / "Artist" / "Album" / "01.flac").touch()
    (root / "Empty").mkdir()
    (root / "loose.mp3").touch()
    return Library(root)


class TestBuildHostMenu:
    """Tests for the build_host_menu function"""

    def test_items(self, host):
        menu = build_host_menu(host)
        assert menu.title == "Host"
        assert [item.label for item in menu.items] == [
            "Name: pirate",
            "IP: 192.168.1.20",
            "Shut down",
        ]
        assert menu.items[0] == MenuItem(label="Name: pirate")
        assert menu.items[1] == MenuItem(label="IP: 192.168.1.20")

    def test_no_ip_address(self, host):
        host.ip_address.return_value = None
        assert build_host_menu(host).items[1].label == "IP: not available"

    def test_shutdown_is_confirmed(self, host):
        item = build_host_menu(host).items[2]
        assert item.command is None
        assert item.submenu() == Menu(
            title="Shut down?",
            items=(
                MenuItem(label="Cancel", command=MenuCommand.BACK),
                MenuItem(label="Shut down now", command=MenuCommand.SHUTDOWN),
            ),
        )
        host.shutdown.assert_not_called()


class TestBuildLibraryMenu:
    """Tests for the build_library_menu function"""

    def test_empty_directory(self, library):
        menu = build_library_menu(library, library.directory_path / "Empty")
        assert menu == Menu(title="Empty", items=(MenuItem(label="(empty)"),))

    def test_root(self, library):
        root = library.directory_path
        menu = build_library_menu(library)
        assert menu.title == "Library"
        assert [item.label for item in menu.items] == [
            "Play this folder",
            "Artist",
            "Empty",
            "loose.mp3",
        ]
        assert menu.items[0] == MenuItem(
            label="Play this folder",
            command=MenuCommand.PLAY,
            path=root,
        )
        assert menu.items[3] == MenuItem(
            label="loose.mp3",
            command=MenuCommand.PLAY,
            path=root / "loose.mp3",
        )

    def test_subdirectories_are_built_when_opened(self, library):
        root = library.directory_path
        artist = build_library_menu(library).items[1].submenu()
        assert artist.title == "Artist"
        assert [item.label for item in artist.items] == ["Play this folder", "Album"]
        assert artist.items[0].path == root / "Artist"
        album = artist.items[1].submenu()
        assert album.title == "Album"
        assert album.items[1] == MenuItem(
            label="01.flac",
            command=MenuCommand.PLAY,
            path=root / "Artist" / "Album" / "01.flac",
        )


class TestBuildRootMenu:
    """Tests for the build_root_menu function"""

    def test_items(self, library, host):
        menu = build_root_menu(library, host, Settings())
        assert menu.title == "Menu"
        labels = [item.label for item in menu.items]
        assert labels == ["Library", "Settings", "Host", "Back to playback"]
        assert menu.items[0].submenu().title == "Library"
        assert menu.items[1].submenu().title == "Settings"
        assert menu.items[2].submenu().title == "Host"
        assert menu.items[3] == MenuItem(label="Back to playback", command=MenuCommand.CLOSE)

    def test_settings_menu_shows_the_current_values(self, library, host):
        settings = Settings()
        item = build_root_menu(library, host, settings).items[1]
        assert item.submenu().items[0].checked is True
        settings.show_side_icons = False
        assert item.submenu().items[0].checked is False

    def test_submenus_are_built_when_opened(self, library, host):
        build_root_menu(library, host, Settings())
        host.hostname.assert_not_called()


class TestBuildSettingsMenu:
    """Tests for the build_settings_menu function"""

    @pytest.mark.parametrize("show", [True, False])
    def test_side_icons(self, show):
        menu = build_settings_menu(Settings(show_side_icons=show))
        assert menu == Menu(
            title="Settings",
            items=(
                MenuItem(
                    label="Side icons",
                    checked=show,
                    command=MenuCommand.TOGGLE_SIDE_ICONS,
                ),
            ),
        )

    def test_other_items_are_not_checkable(self, library, host):
        menu = build_root_menu(library, host, Settings())
        assert [item.checked for item in menu.items] == [None] * 4


class TestMenu:
    """Tests for the Menu class"""

    def test_empty(self):
        menu = Menu(title="Empty", items=())
        menu.move(1)
        assert menu.selected_index == 0
        assert menu.selected is None

    def test_move(self):
        items = (MenuItem(label="a"), MenuItem(label="b"), MenuItem(label="c"))
        menu = Menu(title="Letters", items=items)
        assert menu.selected == items[0]
        menu.move(1)
        assert menu.selected == items[1]
        menu.move(-1)
        assert menu.selected == items[0]

    def test_move_wraps_around(self):
        items = (MenuItem(label="a"), MenuItem(label="b"), MenuItem(label="c"))
        menu = Menu(title="Letters", items=items)
        menu.move(-1)
        assert menu.selected == items[2]
        menu.move(1)
        assert menu.selected == items[0]
