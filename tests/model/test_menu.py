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
    build_display_menu,
    build_host_menu,
    build_library_menu,
    build_root_menu,
    build_settings_menu,
    build_startup_fixed_volume_menu,
    build_startup_menu,
    build_startup_playlist_menu,
    build_startup_volume_menu,
)
from mocassino.model.settings import Settings, StartupPlaylist, StartupVolume


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


class TestBuildDisplayMenu:
    """Tests for the build_display_menu function"""

    @pytest.mark.parametrize("show", [True, False])
    def test_side_icons(self, show):
        menu = build_display_menu(Settings(show_side_icons=show))
        assert menu == Menu(
            title="Display",
            items=(
                MenuItem(
                    label="Show side icons",
                    checked=show,
                    command=MenuCommand.TOGGLE_SIDE_ICONS,
                ),
            ),
        )


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
        assert item.submenu().items[0].submenu().items[0].checked is True
        settings.show_side_icons = False
        assert item.submenu().items[0].submenu().items[0].checked is False

    def test_submenus_are_built_when_opened(self, library, host):
        build_root_menu(library, host, Settings())
        host.hostname.assert_not_called()


class TestBuildSettingsMenu:
    """Tests for the build_settings_menu function"""

    def test_items(self):
        menu = build_settings_menu(Settings())
        assert menu.title == "Settings"
        assert [item.label for item in menu.items] == ["Display", "Startup"]
        assert [item.checked for item in menu.items] == [None, None]
        assert [item.command for item in menu.items] == [None, None]
        assert menu.items[0].submenu().title == "Display"
        assert menu.items[1].submenu().title == "Startup"

    def test_submenus_show_the_current_values(self):
        settings = Settings()
        display, startup = build_settings_menu(settings).items
        assert display.submenu().items[0].checked is True
        assert startup.submenu().items[2].submenu().selected.label == "Use saved"
        settings.show_side_icons = False
        settings.startup_volume = StartupVolume.USE_FIXED
        assert display.submenu().items[0].checked is False
        assert startup.submenu().items[2].submenu().selected.label == "Use fixed"

    def test_other_items_are_not_checkable(self, library, host):
        menu = build_root_menu(library, host, Settings())
        assert [item.checked for item in menu.items] == [None] * 4


class TestBuildStartupFixedVolumeMenu:
    """Tests for the build_startup_fixed_volume_menu function"""

    def test_choices(self):
        menu = build_startup_fixed_volume_menu(Settings(startup_fixed_volume=35))
        assert menu.title == "Fixed volume"
        assert [item.label for item in menu.items] == [str(volume) for volume in range(0, 101, 5)]
        assert [item.value for item in menu.items] == [item.label for item in menu.items]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_FIXED_VOLUME}
        assert [item.label for item in menu.items if item.checked] == ["35"]
        assert [item.checked for item in menu.items].count(False) == 20
        assert menu.selected.label == "35"

    @pytest.mark.parametrize(("volume", "label"), [(0, "0"), (100, "100"), (50, "50")])
    def test_current_volume_is_selected(self, volume, label):
        menu = build_startup_fixed_volume_menu(Settings(startup_fixed_volume=volume))
        assert menu.selected.label == label
        assert menu.selected.checked is True

    @pytest.mark.parametrize(("volume", "label"), [(37, "35"), (38, "40"), (99, "100"), (2, "0")])
    def test_volume_not_among_the_choices(self, volume, label):
        menu = build_startup_fixed_volume_menu(Settings(startup_fixed_volume=volume))
        assert menu.selected.label == label
        assert [item for item in menu.items if item.checked] == []


class TestBuildStartupMenu:
    """Tests for the build_startup_menu function"""

    def test_items(self):
        menu = build_startup_menu(Settings())
        assert menu.title == "Startup"
        assert [item.label for item in menu.items] == ["Fixed volume", "Playlist", "Volume"]
        assert [item.checked for item in menu.items] == [None, None, None]
        assert [item.command for item in menu.items] == [None, None, None]

    def test_fixed_volume_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[0]
        assert item.submenu().title == "Fixed volume"
        assert item.submenu().selected.label == "50"
        settings.startup_fixed_volume = 85
        assert item.submenu().selected.label == "85"

    def test_volume_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[2]
        assert item.submenu().title == "Volume"
        assert item.submenu().selected.label == "Use saved"
        settings.startup_volume = StartupVolume.USE_FIXED
        assert item.submenu().selected.label == "Use fixed"

    def test_playlist_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[1]
        assert item.checked is None
        assert item.command is None
        assert item.submenu().title == "Playlist"
        settings.startup_playlist = StartupPlaylist.USE_MOCP_STATE
        assert item.submenu().selected.label == "Use mocp state"


class TestBuildStartupPlaylistMenu:
    """Tests for the build_startup_playlist_menu function"""

    @pytest.mark.parametrize(
        ("choice", "index"),
        [
            (StartupPlaylist.SELECT_FROM_LIBRARY, 0),
            (StartupPlaylist.USE_MOCP_STATE, 1),
            (StartupPlaylist.USE_SAVED, 2),
        ],
    )
    def test_choices(self, choice, index):
        menu = build_startup_playlist_menu(Settings(startup_playlist=choice))
        assert menu.title == "Playlist"
        assert [item.label for item in menu.items] == [
            "Select from library",
            "Use mocp state",
            "Use saved",
        ]
        assert [item.value for item in menu.items] == [
            "select_from_library",
            "use_mocp_state",
            "use_saved",
        ]
        assert [item.checked for item in menu.items] == [position == index for position in range(3)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_PLAYLIST}
        assert menu.selected_index == index


class TestBuildStartupVolumeMenu:
    """Tests for the build_startup_volume_menu function"""

    @pytest.mark.parametrize(
        ("choice", "index"),
        [(StartupVolume.USE_FIXED, 0), (StartupVolume.USE_SAVED, 1)],
    )
    def test_choices(self, choice, index):
        menu = build_startup_volume_menu(Settings(startup_volume=choice))
        assert menu.title == "Volume"
        assert [item.label for item in menu.items] == ["Use fixed", "Use saved"]
        assert [item.value for item in menu.items] == ["use_fixed", "use_saved"]
        assert [item.checked for item in menu.items] == [position == index for position in range(2)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_VOLUME}
        assert menu.selected_index == index


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
