"""Tests for the menus.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.constants import (
    MocStateOnExit,
    RightTimerValue,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.model.colors import COLOR_NAMES
from mocassino.model.library import Library
from mocassino.model.menu import (
    Menu,
    MenuCommand,
    MenuItem,
    _label,
    build_display_brightness_menu,
    build_display_color_menu,
    build_display_colors_menu,
    build_display_menu,
    build_display_orientation_menu,
    build_display_right_timer_value_menu,
    build_display_timeout_menu,
    build_display_ui_elements_menu,
    build_library_menu,
    build_playback_menu,
    build_playback_seek_step_menu,
    build_playback_volume_default_menu,
    build_playback_volume_step_menu,
    build_root_menu,
    build_save_state_menu,
    build_settings_menu,
    build_startup_menu,
    build_startup_playlist_menu,
    build_startup_state_menu,
    build_startup_volume_menu,
    build_system_menu,
    build_system_moc_state_on_exit_menu,
)
from mocassino.model.settings import Settings
from mocassino.model.system import System


@pytest.fixture
def system(mocker):
    system = mocker.create_autospec(System, instance=True)
    system.hostname.return_value = "pirate"
    system.ip_address.return_value = "192.168.1.20"
    return system


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

    def test_items(self):
        menu = build_display_menu(Settings())
        assert menu.title == "Display"
        assert [item.label for item in menu.items] == [
            "Brightness (%)",
            "Colors",
            "Orientation",
            "Timeout (s)",
            "UI elements",
        ]
        assert all(item.checked is None and item.command is None for item in menu.items)

    def test_ui_elements_submenu(self):
        settings = Settings()
        item = build_display_menu(settings).items[4]
        assert item.submenu().title == "UI elements"
        assert item.submenu().items[3].checked is True
        settings.show_side_icons = False
        assert item.submenu().items[3].checked is False

    def test_colors_submenu(self):
        settings = Settings()
        item = build_display_menu(settings).items[1]
        assert item.checked is None
        assert item.command is None
        assert item.submenu().title == "Colors"

    def test_brightness_submenu(self):
        settings = Settings()
        item = build_display_menu(settings).items[0]
        assert item.checked is None
        assert item.command is None
        assert item.submenu().title == "Brightness (%)"
        assert item.submenu().selected.label == "100"
        settings.display_brightness = 45
        assert item.submenu().selected.label == "45"

    def test_timeout_submenu(self):
        settings = Settings()
        item = build_display_menu(settings).items[3]
        assert item.submenu().title == "Timeout (s)"
        assert item.submenu().selected.label == "60"
        settings.display_timeout = 0
        assert item.submenu().selected.label == "No timeout"

    def test_orientation_submenu(self):
        settings = Settings()
        item = build_display_menu(settings).items[2]
        assert item.checked is None
        assert item.command is None
        assert item.submenu().title == "Orientation"
        assert item.submenu().selected.label == "0"
        settings.display_orientation = 270
        assert item.submenu().selected.label == "270"


class TestBuildDisplayColorMenu:
    """Tests for the build_display_color_menu function"""

    @pytest.mark.parametrize("role", ["accented", "background", "muted", "normal", "track"])
    def test_default(self, role):
        settings = Settings()
        menu = build_display_color_menu(settings, role)
        current = getattr(settings, f"display_colors_{role}")
        assert menu.title == role.capitalize()
        assert len(menu.items) == 140
        assert menu.selected.label == f"{current} [X]"
        assert menu.selected.color == current
        assert [item.label for item in menu.items if item.label.endswith(" [X]")] == [
            f"{current} [X]"
        ]
        command = MenuCommand(f"set_display_colors_{role}")
        assert all(item.command is command for item in menu.items)
        assert all(item.checked is None for item in menu.items)
        assert all(item.color == item.value for item in menu.items)
        assert [item.value for item in menu.items] == list(COLOR_NAMES)

    def test_items(self):
        menu = build_display_color_menu(Settings(), "accented")
        assert menu.items[0] == MenuItem(
            label="black",
            color="black",
            command=MenuCommand.SET_DISPLAY_COLORS_ACCENTED,
            value="black",
        )
        assert "darkgrey" not in [item.label for item in menu.items]

    @pytest.mark.parametrize(
        ("spec", "label"),
        [("cyan", "cyan [X]"), ("#00FFFF", "aqua [X]"), ("DarkGrey", "darkgray [X]")],
    )
    def test_named_current(self, spec, label):
        menu = build_display_color_menu(Settings(display_colors_track=spec), "track")
        assert len(menu.items) == 140
        assert menu.selected.label == label
        assert menu.selected.command is MenuCommand.SET_DISPLAY_COLORS_TRACK

    def test_unnamed_current(self):
        menu = build_display_color_menu(Settings(display_colors_muted="#123456"), "muted")
        assert len(menu.items) == 141
        assert menu.selected_index == 0
        assert menu.items[0] == MenuItem(label="#123456 [X]", color="#123456")
        assert menu.items[1].label == "black"
        assert not [item for item in menu.items[1:] if item.label.endswith(" [X]")]


class TestBuildDisplayColorsMenu:
    """Tests for the build_display_colors_menu function"""

    def test_items(self):
        settings = Settings()
        menu = build_display_colors_menu(settings)
        assert menu.title == "Colors"
        labels = ["Accented", "Background", "Muted", "Normal", "Track"]
        assert [item.label for item in menu.items] == [*labels, "Reset all colors"]
        assert [item.submenu().title for item in menu.items[:5]] == labels
        assert all(item.command is None and item.checked is None for item in menu.items)
        settings.display_colors_normal = "gold"
        assert menu.items[3].submenu().selected.label == "gold [X]"

    def test_reset_all_colors_is_confirmed(self):
        item = build_display_colors_menu(Settings()).items[5]
        assert item.submenu() == Menu(
            title="Reset all colors?",
            items=(
                MenuItem(label="Cancel", command=MenuCommand.BACK),
                MenuItem(label="Reset now", command=MenuCommand.RESET_ALL_COLORS),
            ),
        )


class TestBuildDisplayTimeoutMenu:
    """Tests for the build_display_timeout_menu function"""

    def test_choices(self):
        menu = build_display_timeout_menu(Settings())
        assert menu.title == "Timeout (s)"
        assert [item.label for item in menu.items] == [
            "No timeout",
            "5",
            "10",
            "15",
            "20",
            "30",
            "60",
            "120",
            "300",
        ]
        assert [item.value for item in menu.items] == [
            "0",
            "5",
            "10",
            "15",
            "20",
            "30",
            "60",
            "120",
            "300",
        ]
        assert {item.command for item in menu.items} == {MenuCommand.SET_DISPLAY_TIMEOUT}
        assert [item.label for item in menu.items if item.checked] == ["60"]
        assert menu.selected.label == "60"

    @pytest.mark.parametrize(("timeout", "label"), [(0, "No timeout"), (5, "5"), (300, "300")])
    def test_current(self, timeout, label):
        menu = build_display_timeout_menu(Settings(display_timeout=timeout))
        assert menu.selected.label == label
        assert [item.label for item in menu.items if item.checked] == [label]


class TestBuildDisplayUiElementsMenu:
    """Tests for the build_display_ui_elements_menu function"""

    def test_items(self):
        menu = build_display_ui_elements_menu(Settings())
        assert menu.title == "UI elements"
        assert [item.label for item in menu.items] == [
            "Right timer value",
            "Show playlist bar",
            "Show progress bar",
            "Show side icons",
            "Show timers",
            "Show volume bar",
        ]
        assert [item.label for item in menu.items] == sorted(item.label for item in menu.items)
        assert [item.command for item in menu.items] == [
            None,
            MenuCommand.TOGGLE_PLAYLIST_BAR,
            MenuCommand.TOGGLE_PROGRESS_BAR,
            MenuCommand.TOGGLE_SIDE_ICONS,
            MenuCommand.TOGGLE_TIMERS,
            MenuCommand.TOGGLE_VOLUME_BAR,
        ]
        assert all(item.submenu is None for item in menu.items[1:])
        right_timer_value = menu.items[0]
        assert right_timer_value.checked is None
        assert right_timer_value.submenu is not None
        assert right_timer_value.submenu().title == "Right timer value"

    @pytest.mark.parametrize(
        ("index", "attribute"),
        [
            (1, "show_playlist_bar"),
            (2, "show_progress_bar"),
            (3, "show_side_icons"),
            (4, "show_timers"),
            (5, "show_volume_bar"),
        ],
    )
    @pytest.mark.parametrize("show", [True, False])
    def test_checked(self, index, attribute, show):
        settings = Settings(**{attribute: show})
        menu = build_display_ui_elements_menu(settings)
        assert menu.items[index].checked is show
        assert [item.checked for item in menu.items].count(True) == (5 if show else 4)


class TestBuildDisplayRightTimerValueMenu:
    """Tests for the build_display_right_timer_value_menu function"""

    @pytest.mark.parametrize(
        ("value", "index"), [(RightTimerValue.END_TIME, 0), (RightTimerValue.REMAINING_TIME, 1)]
    )
    def test_choices(self, value, index):
        menu = build_display_right_timer_value_menu(Settings(right_timer_value=value))
        assert menu.title == "Right timer value"
        assert [item.label for item in menu.items] == ["End time", "Remaining time"]
        assert [item.value for item in menu.items] == ["end_time", "remaining_time"]
        assert all(item.command is MenuCommand.SET_RIGHT_TIMER_VALUE for item in menu.items)
        assert [item.checked for item in menu.items] == [index == 0, index == 1]
        assert menu.selected_index == index


class TestBuildDisplayBrightnessMenu:
    """Tests for the build_display_brightness_menu function"""

    def test_choices(self):
        menu = build_display_brightness_menu(Settings(display_brightness=35))
        assert menu.title == "Brightness (%)"
        labels = [str(brightness) for brightness in range(0, 101, 5)]
        assert [item.label for item in menu.items] == labels
        assert [item.value for item in menu.items] == labels
        assert {item.command for item in menu.items} == {MenuCommand.SET_DISPLAY_BRIGHTNESS}
        assert [item.label for item in menu.items if item.checked] == ["35"]
        assert menu.selected.label == "35"

    @pytest.mark.parametrize(("brightness", "label"), [(33, "35"), (32, "30"), (99, "100")])
    def test_brightness_not_among_the_choices(self, brightness, label):
        menu = build_display_brightness_menu(Settings(display_brightness=brightness))
        assert menu.selected.label == label
        assert [item for item in menu.items if item.checked] == []


class TestBuildDisplayOrientationMenu:
    """Tests for the build_display_orientation_menu function"""

    @pytest.mark.parametrize(("orientation", "index"), [(0, 0), (90, 1), (180, 2), (270, 3)])
    def test_choices(self, orientation, index):
        menu = build_display_orientation_menu(Settings(display_orientation=orientation))
        assert menu.title == "Orientation"
        assert [item.label for item in menu.items] == ["0", "90", "180", "270"]
        assert [item.value for item in menu.items] == ["0", "90", "180", "270"]
        assert [item.checked for item in menu.items] == [position == index for position in range(4)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_DISPLAY_ORIENTATION}
        assert menu.selected_index == index

    def test_orientation_not_among_the_choices(self):
        menu = build_display_orientation_menu(Settings(display_orientation=45))
        assert menu.selected_index == 0
        assert [item for item in menu.items if item.checked] == []


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

    def test_items(self, library, system):
        menu = build_root_menu(library, system, Settings())
        assert menu.title == "Menu"
        labels = [item.label for item in menu.items]
        assert labels == ["Library", "Settings", "System"]
        assert menu.items[0].submenu().title == "Library"
        assert menu.items[1].submenu().title == "Settings"
        assert menu.items[2].submenu().title == "System"

    def test_settings_menu_shows_the_current_values(self, library, system):
        settings = Settings()
        item = build_root_menu(library, system, settings).items[1]
        assert item.submenu().items[0].submenu().items[4].submenu().items[3].checked is True
        settings.show_side_icons = False
        assert item.submenu().items[0].submenu().items[4].submenu().items[3].checked is False

    def test_submenus_are_built_when_opened(self, library, system):
        build_root_menu(library, system, Settings())
        system.hostname.assert_not_called()


class TestBuildSaveStateMenu:
    """Tests for the build_save_state_menu function"""

    def test_items(self):
        menu = build_save_state_menu(Settings())
        assert menu.title == "Save state"
        assert [item.label for item in menu.items] == [
            "On exit",
            "On playback tick",
            "On startup",
            "On state change",
            "On track change",
            "On volume change",
        ]
        assert [item.label for item in menu.items] == sorted(item.label for item in menu.items)
        assert [item.command for item in menu.items] == [
            MenuCommand.TOGGLE_SAVE_STATE_ON_EXIT,
            MenuCommand.TOGGLE_SAVE_STATE_ON_PLAYBACK_TICK,
            MenuCommand.TOGGLE_SAVE_STATE_ON_STARTUP,
            MenuCommand.TOGGLE_SAVE_STATE_ON_STATE_CHANGE,
            MenuCommand.TOGGLE_SAVE_STATE_ON_TRACK_CHANGE,
            MenuCommand.TOGGLE_SAVE_STATE_ON_VOLUME_CHANGE,
        ]
        assert [item.checked for item in menu.items] == [True, False, True, True, True, True]
        assert all(item.submenu is None for item in menu.items)

    @pytest.mark.parametrize(
        ("index", "attribute"),
        [
            (0, "save_state_on_exit"),
            (1, "save_state_on_playback_tick"),
            (2, "save_state_on_startup"),
            (3, "save_state_on_state_change"),
            (4, "save_state_on_track_change"),
            (5, "save_state_on_volume_change"),
        ],
    )
    @pytest.mark.parametrize("on", [True, False])
    def test_checked(self, index, attribute, on):
        menu = build_save_state_menu(Settings(**{attribute: on}))
        assert menu.items[index].checked is on


class TestBuildSettingsMenu:
    """Tests for the build_settings_menu function"""

    def test_items(self):
        menu = build_settings_menu(Settings())
        assert menu.title == "Settings"
        assert [item.label for item in menu.items] == [
            "Display",
            "Playback",
            "MOC state on exit",
            "Save state",
            "Startup",
            "Reset all settings",
        ]
        assert [item.checked for item in menu.items] == [None] * 6
        assert [item.command for item in menu.items] == [None] * 6
        assert menu.items[0].submenu().title == "Display"
        assert menu.items[1].submenu().title == "Playback"
        assert menu.items[2].submenu().title == "MOC state on exit"
        assert menu.items[3].submenu().title == "Save state"
        assert menu.items[4].submenu().title == "Startup"

    def test_moc_state_on_exit_submenu(self):
        settings = Settings()
        item = build_settings_menu(settings).items[2]
        assert item.submenu().selected.label == "Do nothing"
        settings.system_moc_state_on_exit = MocStateOnExit.STOP
        assert item.submenu().selected.label == "Stop"

    def test_reset_all_settings_is_confirmed(self):
        item = build_settings_menu(Settings()).items[5]
        assert item.command is None
        assert item.submenu() == Menu(
            title="Reset all settings?",
            items=(
                MenuItem(label="Cancel", command=MenuCommand.BACK),
                MenuItem(label="Reset now", command=MenuCommand.RESET_ALL_SETTINGS),
            ),
        )

    def test_submenus_show_the_current_values(self):
        settings = Settings()
        display, playback, _, save_state, startup, _ = build_settings_menu(settings).items
        assert playback.submenu().items[0].submenu().selected.label == "10"
        settings.playback_seek_step = 30
        assert playback.submenu().items[0].submenu().selected.label == "30"
        assert display.submenu().items[4].submenu().items[3].checked is True
        assert save_state.submenu().items[0].checked is True
        assert startup.submenu().items[2].submenu().selected.label == "Use saved"
        settings.show_side_icons = False
        settings.save_state_on_exit = False
        settings.startup_volume = StartupVolume.USE_DEFAULT
        assert display.submenu().items[4].submenu().items[3].checked is False
        assert save_state.submenu().items[0].checked is False
        assert startup.submenu().items[2].submenu().selected.label == "Use default"

    def test_other_items_are_not_checkable(self, library, system):
        menu = build_root_menu(library, system, Settings())
        assert [item.checked for item in menu.items] == [None] * 3


class TestBuildPlaybackStepMenus:
    """Tests for the build_playback_seek_step_menu and build_playback_volume_step_menu functions"""

    def test_seek_step(self):
        menu = build_playback_seek_step_menu(Settings(playback_seek_step=30))
        assert menu.title == "Seek step (s)"
        assert [item.label for item in menu.items] == ["1", "2", "5", "10", "30", "60"]
        assert [item.value for item in menu.items] == [item.label for item in menu.items]
        assert {item.command for item in menu.items} == {MenuCommand.SET_PLAYBACK_SEEK_STEP}
        assert [item.label for item in menu.items if item.checked] == ["30"]
        assert menu.selected.label == "30"

    def test_seek_step_default(self):
        assert build_playback_seek_step_menu(Settings()).selected.label == "10"

    def test_volume_step(self):
        menu = build_playback_volume_step_menu(Settings(playback_volume_step=4))
        assert menu.title == "Volume step (%)"
        assert [item.label for item in menu.items] == ["1", "2", "4", "5", "10"]
        assert [item.value for item in menu.items] == [item.label for item in menu.items]
        assert {item.command for item in menu.items} == {MenuCommand.SET_PLAYBACK_VOLUME_STEP}
        assert [item.label for item in menu.items if item.checked] == ["4"]
        assert menu.selected.label == "4"

    def test_volume_step_default(self):
        assert build_playback_volume_step_menu(Settings()).selected.label == "5"

    @pytest.mark.parametrize(("step", "label"), [(3, "2"), (7, "5"), (20, "10"), (45, "30")])
    def test_step_not_among_the_choices(self, step, label):
        menu = build_playback_seek_step_menu(Settings(playback_seek_step=step))
        assert menu.selected.label == label
        assert [item for item in menu.items if item.checked] == []


class TestBuildPlaybackMenu:
    """Tests for the build_playback_menu function"""

    def test_items(self):
        menu = build_playback_menu(Settings())
        assert menu.title == "Playback"
        assert [item.label for item in menu.items] == [
            "Seek step (s)",
            "Volume default (%)",
            "Volume step (%)",
        ]
        assert [item.checked for item in menu.items] == [None] * 3
        assert [item.command for item in menu.items] == [None] * 3
        assert menu.items[0].submenu().title == "Seek step (s)"
        assert menu.items[1].submenu().title == "Volume default (%)"
        assert menu.items[2].submenu().title == "Volume step (%)"

    def test_volume_default_submenu(self):
        settings = Settings()
        item = build_playback_menu(settings).items[1]
        assert item.submenu().title == "Volume default (%)"
        assert item.submenu().selected.label == "50"
        settings.playback_volume_default = 85
        assert item.submenu().selected.label == "85"


class TestBuildPlaybackVolumeDefaultMenu:
    """Tests for the build_playback_volume_default_menu function"""

    def test_choices(self):
        menu = build_playback_volume_default_menu(Settings(playback_volume_default=35))
        assert menu.title == "Volume default (%)"
        assert [item.label for item in menu.items] == [str(volume) for volume in range(0, 101, 5)]
        assert [item.value for item in menu.items] == [item.label for item in menu.items]
        assert {item.command for item in menu.items} == {MenuCommand.SET_PLAYBACK_VOLUME_DEFAULT}
        assert [item.label for item in menu.items if item.checked] == ["35"]
        assert [item.checked for item in menu.items].count(False) == 20
        assert menu.selected.label == "35"

    @pytest.mark.parametrize(("volume", "label"), [(0, "0"), (100, "100"), (50, "50")])
    def test_current_volume_is_selected(self, volume, label):
        menu = build_playback_volume_default_menu(Settings(playback_volume_default=volume))
        assert menu.selected.label == label
        assert menu.selected.checked is True

    @pytest.mark.parametrize(("volume", "label"), [(37, "35"), (38, "40"), (99, "100"), (2, "0")])
    def test_volume_not_among_the_choices(self, volume, label):
        menu = build_playback_volume_default_menu(Settings(playback_volume_default=volume))
        assert menu.selected.label == label
        assert [item for item in menu.items if item.checked] == []


class TestBuildStartupMenu:
    """Tests for the build_startup_menu function"""

    def test_items(self):
        menu = build_startup_menu(Settings())
        assert menu.title == "Startup"
        assert [item.label for item in menu.items] == ["Playlist", "State", "Volume"]
        assert [item.checked for item in menu.items] == [None] * 3
        assert [item.command for item in menu.items] == [None] * 3

    def test_state_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[1]
        assert item.submenu().title == "State"
        assert item.submenu().selected.label == "Use saved"
        settings.startup_state = StartupState.PLAY
        assert item.submenu().selected.label == "Play"

    def test_volume_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[2]
        assert item.submenu().title == "Volume"
        assert item.submenu().selected.label == "Use saved"
        settings.startup_volume = StartupVolume.USE_DEFAULT
        assert item.submenu().selected.label == "Use default"

    def test_playlist_submenu(self):
        settings = Settings()
        item = build_startup_menu(settings).items[0]
        assert item.checked is None
        assert item.command is None
        assert item.submenu().title == "Playlist"
        settings.startup_playlist = StartupPlaylist.USE_MOC_STATE
        assert item.submenu().selected.label == "Use MOC state"


class TestBuildStartupPlaylistMenu:
    """Tests for the build_startup_playlist_menu function"""

    @pytest.mark.parametrize(
        ("choice", "index"),
        [
            (StartupPlaylist.OPEN_LIBRARY, 0),
            (StartupPlaylist.USE_MOC_STATE, 1),
            (StartupPlaylist.USE_SAVED, 2),
        ],
    )
    def test_choices(self, choice, index):
        menu = build_startup_playlist_menu(Settings(startup_playlist=choice))
        assert menu.title == "Playlist"
        assert [item.label for item in menu.items] == [
            "Open library",
            "Use MOC state",
            "Use saved",
        ]
        assert [item.value for item in menu.items] == [
            "open_library",
            "use_moc_state",
            "use_saved",
        ]
        assert [item.checked for item in menu.items] == [position == index for position in range(3)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_PLAYLIST}
        assert menu.selected_index == index


class TestBuildStartupStateMenu:
    """Tests for the build_startup_state_menu function"""

    @pytest.mark.parametrize(
        ("choice", "index"),
        [
            (StartupState.PAUSE, 0),
            (StartupState.PLAY, 1),
            (StartupState.STOP, 2),
            (StartupState.USE_SAVED, 3),
        ],
    )
    def test_choices(self, choice, index):
        menu = build_startup_state_menu(Settings(startup_state=choice))
        assert menu.title == "State"
        assert [item.label for item in menu.items] == ["Pause", "Play", "Stop", "Use saved"]
        assert [item.value for item in menu.items] == ["pause", "play", "stop", "use_saved"]
        assert [item.checked for item in menu.items] == [position == index for position in range(4)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_STATE}
        assert menu.selected_index == index


class TestBuildStartupVolumeMenu:
    """Tests for the build_startup_volume_menu function"""

    @pytest.mark.parametrize(
        ("choice", "index"),
        [(StartupVolume.USE_DEFAULT, 0), (StartupVolume.USE_SAVED, 1)],
    )
    def test_choices(self, choice, index):
        menu = build_startup_volume_menu(Settings(startup_volume=choice))
        assert menu.title == "Volume"
        assert [item.label for item in menu.items] == ["Use default", "Use saved"]
        assert [item.value for item in menu.items] == ["use_default", "use_saved"]
        assert [item.checked for item in menu.items] == [position == index for position in range(2)]
        assert {item.command for item in menu.items} == {MenuCommand.SET_STARTUP_VOLUME}
        assert menu.selected_index == index


class TestBuildSystemMenu:
    """Tests for the build_system_menu function"""

    def test_items(self, system):
        menu = build_system_menu(system)
        assert menu.title == "System"
        assert [item.label for item in menu.items] == [
            "Name: pirate",
            "IP: 192.168.1.20",
            "Reboot",
            "Shut down",
        ]
        assert menu.items[0] == MenuItem(label="Name: pirate")
        assert menu.items[1] == MenuItem(label="IP: 192.168.1.20")

    def test_no_ip_address(self, system):
        system.ip_address.return_value = None
        assert build_system_menu(system).items[1].label == "IP: not available"

    def test_reboot_is_confirmed(self, system):
        item = build_system_menu(system).items[2]
        assert item.command is None
        assert item.submenu() == Menu(
            title="Reboot?",
            items=(
                MenuItem(label="Cancel", command=MenuCommand.BACK),
                MenuItem(label="Reboot now", command=MenuCommand.REBOOT),
            ),
        )
        system.reboot.assert_not_called()

    def test_shutdown_is_confirmed(self, system):
        item = build_system_menu(system).items[3]
        assert item.command is None
        assert item.submenu() == Menu(
            title="Shut down?",
            items=(
                MenuItem(label="Cancel", command=MenuCommand.BACK),
                MenuItem(label="Shut down now", command=MenuCommand.SHUTDOWN),
            ),
        )
        system.shutdown.assert_not_called()


class TestBuildSystemMocStateOnExitMenu:
    """Tests for the build_system_moc_state_on_exit_menu function"""

    @pytest.mark.parametrize("choice", list(MocStateOnExit))
    def test_choices(self, choice):
        menu = build_system_moc_state_on_exit_menu(Settings(system_moc_state_on_exit=choice))
        assert menu.title == "MOC state on exit"
        assert [item.label for item in menu.items] == ["Do nothing", "Pause", "Quit", "Stop"]
        assert [item.value for item in menu.items] == ["do_nothing", "pause", "quit", "stop"]
        assert {item.command for item in menu.items} == {MenuCommand.SET_SYSTEM_MOC_STATE_ON_EXIT}
        assert [item.value for item in menu.items if item.checked] == [choice.value]
        assert menu.selected.value == choice.value


class TestLabel:
    """Tests for the _label function"""

    @pytest.mark.parametrize(
        ("value", "label"),
        [
            ("do_nothing", "Do nothing"),
            ("moc", "MOC"),
            ("open_library", "Open library"),
            ("pause", "Pause"),
            ("use_moc_state", "Use MOC state"),
            ("use_saved", "Use saved"),
        ],
    )
    def test_label(self, value, label):
        assert _label(value) == label


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
