"""Tests for the controller.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.constants import (
    Button,
    ButtonPress,
    MocStateOnExit,
    Mode,
    RightTimerValue,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.controller.actions import resolve_button_map
from mocassino.controller.controller import Controller
from mocassino.controller.events import ButtonEvent
from mocassino.defaults import DEFAULT_BUTTON_MAP
from mocassino.model.library import Library
from mocassino.model.menu import Menu, MenuCommand, MenuItem
from mocassino.model.moc import (
    MocError,
    MocServerNotRunningError,
    MocState,
    MocStatus,
    SubprocessMocClient,
)
from mocassino.model.settings import Settings
from mocassino.model.state import AppState
from mocassino.model.system import System, SystemShutdownError

A = ButtonEvent(Button.A)
A_LONG = ButtonEvent(Button.A, ButtonPress.LONG)
B = ButtonEvent(Button.B)
B_LONG = ButtonEvent(Button.B, ButtonPress.LONG)
X = ButtonEvent(Button.X)
X_HOLD = ButtonEvent(Button.X, ButtonPress.HOLD)
X_LONG = ButtonEvent(Button.X, ButtonPress.LONG)
Y = ButtonEvent(Button.Y)
Y_HOLD = ButtonEvent(Button.Y, ButtonPress.HOLD)
Y_LONG = ButtonEvent(Button.Y, ButtonPress.LONG)


@pytest.fixture
def system(mocker):
    system = mocker.create_autospec(System, instance=True)
    system.hostname.return_value = "pirate"
    system.ip_address.return_value = "192.168.1.20"
    return system


@pytest.fixture
def library(tmp_path):
    """Create a library with an album of one track."""
    root = tmp_path / "music"
    (root / "Album").mkdir(parents=True)
    (root / "Album" / "01.flac").touch()
    return Library(root)


@pytest.fixture
def moc(mocker):
    return mocker.create_autospec(SubprocessMocClient, instance=True)


@pytest.fixture
def state():
    return AppState(status=MocStatus(state=MocState.PLAY), volume=50)


@pytest.fixture
def controller(state, moc, library, system):
    return Controller(state, moc, library, system, DEFAULT_BUTTON_MAP)


def open_single_item_menu(state, item) -> None:
    """Open a menu having only the given item, on top of another menu."""
    state.open_menu(Menu(title="Below", items=()))
    state.open_menu(Menu(title="Above", items=(item,)))


class TestController:
    """Tests for the Controller class"""

    def test_custom_button_map(self, state, moc, library, system):
        button_map = {"playback": {"X_long": "next"}}
        controller = Controller(state, moc, library, system, button_map)
        controller.handle(X_LONG)
        moc.next.assert_called_once_with()
        controller.handle(A)
        moc.toggle_pause.assert_not_called()

    def test_host_error_is_logged(self, controller, state, system, caplog):
        system.shutdown.side_effect = SystemShutdownError("denied")
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        with caplog.at_level(logging.ERROR):
            controller.handle(B)
        assert "Cannot perform menu_select: denied" in caplog.text
        assert state.shutting_down is False

    def test_invalid_button_map(self, state, moc, library, system):
        with pytest.raises(ValueError, match="is not a valid"):
            Controller(state, moc, library, system, {"menu": {"A": "rewind"}})

    def test_menu_actions_without_menu(self, state, moc, library, system):
        button_map = {"playback": {"A": "menu_select", "B": "menu_back", "X": "menu_up"}}
        controller = Controller(state, moc, library, system, button_map)
        for event in (A, B, X):
            controller.handle(event)
        assert state.mode == Mode.PLAYBACK

    def test_menu_back(self, controller, state):
        controller.handle(A_LONG)
        controller.handle(B)
        assert len(state.menus) == 2
        controller.handle(A)
        assert len(state.menus) == 1
        controller.handle(A)
        assert state.mode == Mode.PLAYBACK

    def test_menu_navigation(self, controller, state):
        controller.handle(A_LONG)
        menu = state.current_menu
        assert menu.selected.label == "Library"
        controller.handle(Y)
        assert menu.selected.label == "Settings"
        controller.handle(X)
        assert menu.selected.label == "Library"
        controller.handle(X)
        assert menu.selected.label == "System"

    def test_menu_select_back(self, controller, state):
        open_single_item_menu(state, MenuItem(label="Cancel", command=MenuCommand.BACK))
        controller.handle(B)
        assert state.current_menu.title == "Below"

    @pytest.mark.parametrize("event", [B, X_LONG, Y_LONG])
    def test_menu_select_buttons(self, controller, state, event):
        controller.handle(A_LONG)
        controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Library"]

    def test_menu_select_empty_menu(self, controller, state):
        state.open_menu(Menu(title="Empty", items=()))
        controller.handle(B)
        assert state.current_menu.title == "Empty"

    def test_menu_select_information(self, controller, state, moc, system):
        open_single_item_menu(state, MenuItem(label="Name: pirate"))
        controller.handle(B)
        assert state.current_menu.title == "Above"
        assert moc.mock_calls == []
        system.shutdown.assert_not_called()

    def test_menu_select_play(self, controller, state, moc, library):
        controller.handle(A_LONG)
        controller.handle(B)
        assert state.current_menu.title == "Library"
        controller.handle(Y)
        controller.handle(B)
        assert state.current_menu.title == "Album"
        controller.handle(Y)
        controller.handle(B)
        moc.play.assert_called_once_with(library.directory_path / "Album" / "01.flac")
        assert state.mode == Mode.PLAYBACK
        assert state.played_path == str(library.directory_path / "Album" / "01.flac")

    def test_menu_select_play_folder(self, controller, state, moc, library):
        for event in (A_LONG, B, Y, B, B):
            controller.handle(event)
        moc.play.assert_called_once_with(library.directory_path / "Album")
        assert state.played_path == str(library.directory_path / "Album")

    def test_menu_select_play_fails(self, controller, state, moc):
        moc.play.side_effect = MocError("broken")
        for event in (A_LONG, B, B):
            controller.handle(event)
        assert state.played_path is None

    def test_menu_select_play_without_path(self, controller, state, moc):
        open_single_item_menu(state, MenuItem(label="Broken", command=MenuCommand.PLAY))
        controller.handle(B)
        moc.play.assert_not_called()
        assert state.current_menu.title == "Above"

    def test_menu_select_moc_state_on_exit(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, Y, Y, B, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Run", "MOC state on exit"]
        assert [menu.title for menu in state.menus] == titles
        assert state.current_menu.selected.label == "Do nothing"
        assert state.current_menu.selected.checked is True
        for event in (Y, Y, B):
            controller.handle(event)
        assert state.settings.run_moc_state_on_exit is MocStateOnExit.QUIT
        save_settings.assert_called_once_with(state.settings)
        assert [menu.title for menu in state.menus] == titles
        assert [item.label for item in state.current_menu.items if item.checked] == ["Quit"]
        moc.exit_server.assert_not_called()

    def test_menu_select_reset_all_settings(self, mocker, state, moc, library, system):
        defaults = Settings(display_brightness=70)
        reset_all_settings = mocker.Mock(return_value=defaults)
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            reset_all_settings=reset_all_settings,
            save_settings=save_settings,
        )
        settings = state.settings
        settings.playback_seek_step = 30
        settings.show_side_icons = False
        for event in (A_LONG, Y, B, X):
            controller.handle(event)
        assert state.current_menu.selected.label == "Reset all settings"
        controller.handle(B)
        assert state.current_menu.title == "Reset all settings?"
        assert state.current_menu.selected.label == "Cancel"
        reset_all_settings.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        reset_all_settings.assert_called_once_with()
        save_settings.assert_not_called()
        assert state.settings is settings
        assert settings == defaults
        assert [menu.title for menu in state.menus] == ["Menu", "Settings"]
        assert state.current_menu.selected.label == "Reset all settings"

    def test_menu_select_reset_all_settings_without_callback(self, controller, state):
        state.settings.show_volume_bar = False
        for event in (A_LONG, Y, B, X, B, Y, B):
            controller.handle(event)
        assert state.settings == Settings()
        assert [menu.title for menu in state.menus] == ["Menu", "Settings"]

    def test_menu_select_reset_all_settings_cancelled(self, mocker, state, moc, library, system):
        reset_all_settings = mocker.Mock(return_value=Settings())
        controller = Controller(
            state, moc, library, system, DEFAULT_BUTTON_MAP, reset_all_settings=reset_all_settings
        )
        state.settings.show_volume_bar = False
        for event in (A_LONG, Y, B, X, B, B):
            controller.handle(event)
        reset_all_settings.assert_not_called()
        assert state.settings.show_volume_bar is False
        assert [menu.title for menu in state.menus] == ["Menu", "Settings"]

    def test_menu_select_reboot(self, controller, state, system):
        for event in (A_LONG, Y, Y, B, X, X):
            controller.handle(event)
        assert state.current_menu.selected.label == "Reboot"
        controller.handle(B)
        assert state.current_menu.title == "Reboot?"
        assert state.current_menu.selected.label == "Cancel"
        system.reboot.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        system.reboot.assert_called_once_with()
        system.shutdown.assert_not_called()
        assert state.mode == Mode.PLAYBACK
        assert state.shutting_down is True

    def test_menu_select_reboot_that_fails(self, mocker, state, moc, library, system):
        calls = mocker.Mock()
        system.reboot.side_effect = SystemShutdownError("denied")
        controller = Controller(
            state, moc, library, system, DEFAULT_BUTTON_MAP, switch_display=calls.switch_display
        )
        for event in (A_LONG, Y, Y, B, X, X, B, Y, B):
            controller.handle(event)
        system.reboot.assert_called_once_with()
        assert [call.args for call in calls.switch_display.call_args_list] == [(False,), (True,)]
        assert state.shutting_down is False

    def test_menu_select_shutdown(self, controller, state, system):
        controller.handle(A_LONG)
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(B)
        assert state.current_menu.title == "System"
        controller.handle(X)
        controller.handle(B)
        assert state.current_menu.title == "Shut down?"
        system.shutdown.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        system.shutdown.assert_called_once_with()
        system.reboot.assert_not_called()
        assert state.mode == Mode.PLAYBACK
        assert state.shutting_down is True

    def test_menu_select_shutdown_turns_the_display_off_first(
        self, mocker, state, moc, library, system
    ):
        calls = mocker.Mock()
        system.shutdown.side_effect = calls.shutdown
        controller = Controller(
            state, moc, library, system, DEFAULT_BUTTON_MAP, switch_display=calls.switch_display
        )
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        controller.handle(B)
        assert calls.mock_calls == [mocker.call.switch_display(False), mocker.call.shutdown()]
        assert state.shutting_down is True

    def test_menu_select_shutdown_fails(self, mocker, state, moc, library, system, caplog):
        calls = mocker.Mock()
        calls.shutdown.side_effect = SystemShutdownError("denied")
        system.shutdown.side_effect = calls.shutdown
        controller = Controller(
            state, moc, library, system, DEFAULT_BUTTON_MAP, switch_display=calls.switch_display
        )
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        with caplog.at_level(logging.ERROR):
            controller.handle(B)
        assert calls.mock_calls == [
            mocker.call.switch_display(False),
            mocker.call.shutdown(),
            mocker.call.switch_display(True),
        ]
        assert state.shutting_down is False
        assert "Cannot perform menu_select: denied" in caplog.text

    def test_menu_select_shutdown_is_flagged_before_it_is_asked(self, controller, state, system):
        flags = []
        system.shutdown.side_effect = lambda: flags.append(state.shutting_down)
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        assert state.shutting_down is False
        controller.handle(B)
        assert flags == [True]

    def test_menu_select_toggle_side_icons(self, controller, state):
        controller.handle(A_LONG)
        controller.handle(Y)
        controller.handle(B)
        assert state.current_menu.title == "Settings"
        assert state.current_menu.selected.label == "Display"
        controller.handle(B)
        assert state.current_menu.title == "Display"
        assert state.current_menu.selected.label == "Brightness (%)"
        controller.handle(X)
        assert state.current_menu.selected.label == "UI elements"
        controller.handle(B)
        assert state.current_menu.title == "UI elements"
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(Y)
        assert state.current_menu.selected.label == "Show side icons"
        assert state.current_menu.selected.checked is True
        controller.handle(B)
        assert state.settings.show_side_icons is False
        titles = ["Menu", "Settings", "Display", "UI elements"]
        assert [menu.title for menu in state.menus] == titles
        assert state.current_menu.selected.checked is False
        controller.handle(B)
        assert state.settings.show_side_icons is True
        assert state.current_menu.selected.checked is True
        controller.handle(A)
        controller.handle(B)
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(Y)
        assert state.current_menu.selected.label == "Show side icons"
        assert state.current_menu.selected.checked is True

    @pytest.mark.parametrize(
        ("moves", "label", "attribute"),
        [
            (1, "Show playlist bar", "show_playlist_bar"),
            (2, "Show progress bar", "show_progress_bar"),
            (3, "Show side icons", "show_side_icons"),
            (4, "Show timers", "show_timers"),
            (5, "Show volume bar", "show_volume_bar"),
        ],
    )
    def test_menu_select_toggles_of_the_display(
        self, mocker, state, moc, library, system, moves, label, attribute
    ):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, X, B, *[Y] * moves):
            controller.handle(event)
        assert state.current_menu.title == "UI elements"
        assert state.current_menu.selected.label == label
        assert state.current_menu.selected.checked is True
        controller.handle(B)
        assert getattr(state.settings, attribute) is False
        others = {
            "show_playlist_bar",
            "show_progress_bar",
            "show_side_icons",
            "show_timers",
            "show_volume_bar",
        } - {attribute}
        assert all(getattr(state.settings, other) is True for other in others)
        assert state.current_menu.selected.label == label
        assert state.current_menu.selected.checked is False
        save_settings.assert_called_once_with(state.settings)
        controller.handle(B)
        assert getattr(state.settings, attribute) is True
        assert state.current_menu.selected.checked is True

    @pytest.mark.parametrize(
        ("moves", "label", "attribute"),
        [
            (0, "On exit", "run_save_state_on_exit"),
            (1, "On refresh", "run_save_state_on_refresh"),
            (2, "On startup", "run_save_state_on_startup"),
            (3, "On state change", "run_save_state_on_state_change"),
            (4, "On track change", "run_save_state_on_track_change"),
            (5, "On volume change", "run_save_state_on_volume_change"),
        ],
    )
    def test_menu_select_toggles_of_the_save_state(
        self, mocker, state, moc, library, system, moves, label, attribute
    ):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, Y, Y, B, Y, B, *[Y] * moves):
            controller.handle(event)
        assert state.current_menu.title == "Save state"
        assert state.current_menu.selected.label == label
        before = getattr(state.settings, attribute)
        assert state.current_menu.selected.checked is before
        controller.handle(B)
        assert getattr(state.settings, attribute) is not before
        assert state.current_menu.title == "Save state"
        assert state.current_menu.selected.label == label
        assert state.current_menu.selected.checked is not before
        save_settings.assert_called_once_with(state.settings)

    def test_menu_select_right_timer_value(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, X, B):
            controller.handle(event)
        assert state.current_menu.selected.label == "Right timer value"
        controller.handle(B)
        assert state.current_menu.title == "Right timer value"
        assert state.current_menu.selected.label == "End time"
        assert state.current_menu.selected.checked is True
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.right_timer_value is RightTimerValue.REMAINING_TIME
        assert state.current_menu.title == "Right timer value"
        assert state.current_menu.selected.label == "Remaining time"
        assert state.current_menu.selected.checked is True
        save_settings.assert_called_once_with(state.settings)

    def test_menu_select_display_color(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, Y, B, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Display", "Colors", "Accented"]
        assert [menu.title for menu in state.menus] == titles
        assert state.current_menu.selected.label == "limegreen [X]"
        save_settings.assert_not_called()
        for event in (Y, B):
            controller.handle(event)
        assert state.settings.display_colors_accented == "forestgreen"
        save_settings.assert_called_once_with(state.settings)
        assert [menu.title for menu in state.menus] == titles
        assert state.current_menu.selected.label == "forestgreen [X]"
        assert "limegreen" in [item.label for item in state.current_menu.items]

    def test_menu_select_reset_all_colors(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        settings = state.settings
        settings.display_colors_accented = "red"
        settings.display_colors_track = "#123456"
        settings.display_brightness = 40
        for event in (A_LONG, Y, B, B, Y, B, X):
            controller.handle(event)
        assert state.current_menu.selected.label == "Reset all colors"
        controller.handle(B)
        assert state.current_menu.title == "Reset all colors?"
        assert state.current_menu.selected.label == "Cancel"
        save_settings.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        assert settings.color_specs() == Settings().color_specs()
        assert settings.display_brightness == 40
        save_settings.assert_called_once_with(settings)
        assert [menu.title for menu in state.menus] == ["Menu", "Settings", "Display", "Colors"]
        assert state.current_menu.selected.label == "Reset all colors"

    def test_menu_select_reset_all_colors_cancelled(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state, moc, library, system, DEFAULT_BUTTON_MAP, save_settings=save_settings
        )
        state.settings.display_colors_accented = "red"
        for event in (A_LONG, Y, B, B, Y, B, X, B, B):
            controller.handle(event)
        assert state.settings.display_colors_accented == "red"
        save_settings.assert_not_called()
        assert state.current_menu.title == "Colors"

    def test_menu_select_reset_all_colors_without_saving(self, controller, state):
        state.settings.display_colors_muted = "navy"
        for event in (A_LONG, Y, B, B, Y, B, X, B, Y, B):
            controller.handle(event)
        assert state.settings.display_colors_muted == "silver"

    def test_menu_select_display_color_unnamed_does_nothing(self, controller, state):
        state.settings.display_colors_track = "#123456"
        for event in (A_LONG, Y, B, B, Y, B, X, X, B):
            controller.handle(event)
        assert state.current_menu.title == "Track"
        assert state.current_menu.selected.label == "#123456 [X]"
        controller.handle(B)
        assert state.settings.display_colors_track == "#123456"
        assert state.current_menu.title == "Track"

    def test_menu_select_display_brightness(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Display", "Brightness (%)"]
        assert [menu.title for menu in state.menus] == titles
        menu = state.current_menu
        assert len(menu.items) == 21
        assert menu.selected.label == "100"
        assert menu.selected.checked is True
        save_settings.assert_not_called()
        for event in (X, X, B):
            controller.handle(event)
        assert state.settings.display_brightness == 90
        save_settings.assert_called_once_with(state.settings)
        menu = state.current_menu
        assert [menu.title for menu in state.menus] == titles
        assert menu.selected.label == "90"
        assert [item.label for item in menu.items if item.checked] == ["90"]

    def test_menu_select_display_brightness_without_value(self, controller, state):
        item = MenuItem(label="Broken", command=MenuCommand.SET_DISPLAY_BRIGHTNESS)
        open_single_item_menu(state, item)
        controller.handle(B)
        assert state.settings.display_brightness == 100
        assert state.current_menu.title == "Above"

    def test_menu_select_display_timeout(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, X, X, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Display", "Timeout (s)"]
        assert [menu.title for menu in state.menus] == titles
        assert state.current_menu.selected.label == "60"
        save_settings.assert_not_called()
        for event in (X, B):
            controller.handle(event)
        assert state.settings.display_timeout == 30
        save_settings.assert_called_once_with(state.settings)
        assert [item.label for item in state.current_menu.items if item.checked] == ["30"]
        for event in (X, X, X, X, X, B):
            controller.handle(event)
        assert state.settings.display_timeout == 0
        assert state.current_menu.selected.label == "No timeout"

    def test_menu_select_display_orientation(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, Y, Y, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Display", "Orientation"]
        assert [menu.title for menu in state.menus] == titles
        menu = state.current_menu
        assert [item.label for item in menu.items] == ["0", "90", "180", "270"]
        assert [item.checked for item in menu.items] == [True, False, False, False]
        save_settings.assert_not_called()
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.display_orientation == 180
        save_settings.assert_called_once_with(state.settings)
        assert [menu.title for menu in state.menus] == titles
        assert [item.checked for item in state.current_menu.items] == [False, False, True, False]
        assert state.current_menu.selected.label == "180"

    def test_menu_select_display_orientation_without_saving(self, controller, state):
        for event in (A_LONG, Y, B, B, Y, Y, B, Y, B):
            controller.handle(event)
        assert state.settings.display_orientation == 90

    def test_menu_select_display_orientation_without_value(self, controller, state):
        item = MenuItem(label="Broken", command=MenuCommand.SET_DISPLAY_ORIENTATION)
        open_single_item_menu(state, item)
        controller.handle(B)
        assert state.settings.display_orientation == 0
        assert state.current_menu.title == "Above"

    @pytest.mark.parametrize(
        ("orientation", "play_pause", "next_track", "volume_up", "volume_down"),
        [
            (0, Button.A, Button.B, Button.X, Button.Y),
            (90, Button.X, Button.A, Button.Y, Button.B),
            (180, Button.Y, Button.X, Button.B, Button.A),
            (270, Button.B, Button.Y, Button.A, Button.X),
        ],
    )
    def test_buttons_follow_the_orientation(
        self, controller, state, moc, orientation, play_pause, next_track, volume_up, volume_down
    ):
        state.settings.display_orientation = orientation
        controller.handle(ButtonEvent(play_pause))
        moc.toggle_pause.assert_called_once_with()
        controller.handle(ButtonEvent(next_track))
        moc.next.assert_called_once_with()
        controller.handle(ButtonEvent(volume_up))
        moc.set_volume.assert_called_with(55)
        controller.handle(ButtonEvent(volume_down))
        controller.handle(ButtonEvent(volume_down))
        moc.set_volume.assert_called_with(45)
        controller.handle(ButtonEvent(play_pause, ButtonPress.LONG))
        assert state.mode == Mode.MENU
        controller.handle(ButtonEvent(volume_down))
        assert state.current_menu.selected.label == "Settings"
        controller.handle(ButtonEvent(play_pause))
        assert state.mode == Mode.PLAYBACK

    def test_menu_select_playback_steps(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, Y, B):
            controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Settings", "Playback"]
        assert [item.label for item in state.current_menu.items] == [
            "Seek step (s)",
            "Volume default (%)",
            "Volume step (%)",
        ]
        controller.handle(B)
        assert state.current_menu.title == "Seek step (s)"
        assert state.current_menu.selected.label == "10"
        controller.handle(X)
        controller.handle(B)
        assert state.settings.playback_seek_step == 5
        assert [item.label for item in state.current_menu.items if item.checked] == ["5"]
        save_settings.assert_called_once_with(state.settings)
        for event in (A, Y, Y, B):
            controller.handle(event)
        assert state.current_menu.title == "Volume step (%)"
        assert state.current_menu.selected.label == "5"
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.playback_volume_step == 10
        assert [item.label for item in state.current_menu.items if item.checked] == ["10"]
        assert save_settings.call_count == 2

    def test_playback_steps_take_effect_at_once(self, controller, state, moc):
        state.settings.playback_seek_step = 30
        state.settings.playback_volume_step = 2
        controller.handle(X_HOLD)
        moc.seek.assert_called_once_with(30)
        controller.handle(Y_HOLD)
        moc.seek.assert_called_with(-30)
        controller.handle(X)
        moc.set_volume.assert_called_with(52)
        controller.handle(Y)
        controller.handle(Y)
        moc.set_volume.assert_called_with(48)
        assert state.volume == 48

    def test_menu_select_playback_volume_default(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, Y, B, Y, B):
            controller.handle(event)
        titles = ["Menu", "Settings", "Playback", "Volume default (%)"]
        assert [menu.title for menu in state.menus] == titles
        menu = state.current_menu
        assert len(menu.items) == 21
        assert menu.selected.label == "50"
        assert menu.selected.checked is True
        save_settings.assert_not_called()
        for event in (Y, Y, B):
            controller.handle(event)
        assert state.settings.playback_volume_default == 60
        save_settings.assert_called_once_with(state.settings)
        menu = state.current_menu
        assert [menu.title for menu in state.menus] == titles
        assert menu.selected.label == "60"
        assert [item.label for item in menu.items if item.checked] == ["60"]
        assert state.volume == 50
        moc.set_volume.assert_not_called()

    def test_menu_select_playback_volume_default_without_saving(self, controller, state):
        for event in (A_LONG, Y, B, Y, B, Y, B, X, B):
            controller.handle(event)
        assert state.settings.playback_volume_default == 45

    def test_menu_select_playback_volume_default_without_value(self, controller, state):
        item = MenuItem(label="Broken", command=MenuCommand.SET_PLAYBACK_VOLUME_DEFAULT)
        open_single_item_menu(state, item)
        controller.handle(B)
        assert state.settings.playback_volume_default == 50
        assert state.current_menu.title == "Above"

    def test_menu_select_startup_state(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, X, X, B, Y, B):
            controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Settings", "Startup", "State"]
        menu = state.current_menu
        assert [item.label for item in menu.items] == ["Pause", "Play", "Stop", "Use saved"]
        assert [item.checked for item in menu.items] == [False, False, False, True]
        assert menu.selected.label == "Use saved"
        save_settings.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.startup_state is StartupState.PAUSE
        save_settings.assert_called_once_with(state.settings)
        assert [item.checked for item in state.current_menu.items] == [True, False, False, False]
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.startup_state is StartupState.STOP
        assert state.current_menu.selected.label == "Stop"
        moc.stop.assert_not_called()
        moc.pause.assert_not_called()

    def test_menu_select_startup_volume(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, X, X, B, X, B):
            controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Settings", "Startup", "Volume"]
        menu = state.current_menu
        assert [item.label for item in menu.items] == ["Use default", "Use saved"]
        assert [item.checked for item in menu.items] == [False, True]
        assert menu.selected.label == "Use saved"
        save_settings.assert_not_called()
        controller.handle(X)
        controller.handle(B)
        assert state.settings.startup_volume is StartupVolume.USE_DEFAULT
        save_settings.assert_called_once_with(state.settings)
        menu = state.current_menu
        assert menu.title == "Volume"
        assert [item.checked for item in menu.items] == [True, False]
        assert menu.selected.label == "Use default"
        assert state.settings.show_side_icons is True
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.startup_volume is StartupVolume.USE_SAVED
        assert [item.checked for item in state.current_menu.items] == [False, True]

    def test_menu_select_startup_volume_without_saving(self, controller, state):
        for event in (A_LONG, Y, B, X, X, B, X, B, X, B):
            controller.handle(event)
        assert state.settings.startup_volume is StartupVolume.USE_DEFAULT

    def test_menu_select_startup_volume_without_value(self, controller, state):
        item = MenuItem(label="Broken", command=MenuCommand.SET_STARTUP_VOLUME)
        open_single_item_menu(state, item)
        controller.handle(B)
        assert state.settings.startup_volume is StartupVolume.USE_SAVED
        assert state.current_menu.title == "Above"

    def test_menu_select_startup_playlist(self, mocker, state, moc, library, system):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, X, X, B, B):
            controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Settings", "Startup", "Playlist"]
        menu = state.current_menu
        assert [item.label for item in menu.items] == [
            "Open library",
            "Use MOC state",
            "Use saved",
        ]
        assert [item.checked for item in menu.items] == [False, False, True]
        assert menu.selected.label == "Use saved"
        save_settings.assert_not_called()
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(B)
        assert state.settings.startup_playlist is StartupPlaylist.USE_MOC_STATE
        save_settings.assert_called_once_with(state.settings)
        menu = state.current_menu
        assert menu.title == "Playlist"
        assert [item.checked for item in menu.items] == [False, True, False]
        assert menu.selected.label == "Use MOC state"
        controller.handle(X)
        controller.handle(B)
        assert state.settings.startup_playlist is StartupPlaylist.OPEN_LIBRARY
        assert [item.checked for item in state.current_menu.items] == [True, False, False]
        assert save_settings.call_count == 2

    def test_menu_select_startup_playlist_without_saving(self, controller, state):
        for event in (A_LONG, Y, B, X, X, B, B, Y, B):
            controller.handle(event)
        assert state.settings.startup_playlist is StartupPlaylist.OPEN_LIBRARY

    def test_menu_select_startup_playlist_without_value(self, controller, state):
        item = MenuItem(label="Broken", command=MenuCommand.SET_STARTUP_PLAYLIST)
        open_single_item_menu(state, item)
        controller.handle(B)
        assert state.settings.startup_playlist is StartupPlaylist.USE_SAVED
        assert state.current_menu.title == "Above"

    def test_choose_folder(self, controller, state):
        state.open_menu(Menu(title="Old", items=()))
        controller.choose_folder()
        assert [menu.title for menu in state.menus] == ["Menu", "Library"]
        assert state.current_menu.selected.label == "Play this folder"
        controller.handle(A)
        assert [menu.title for menu in state.menus] == ["Menu"]

    def test_menu_select_toggle_side_icons_saves_the_settings(
        self, mocker, state, moc, library, system
    ):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            system,
            DEFAULT_BUTTON_MAP,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B, B, X, B, Y, Y, Y):
            controller.handle(event)
        save_settings.assert_not_called()
        controller.handle(B)
        save_settings.assert_called_once_with(state.settings)
        assert state.settings.show_side_icons is False

    def test_moc_error_is_logged(self, controller, moc, caplog):
        moc.next.side_effect = MocError("broken")
        with caplog.at_level(logging.ERROR):
            controller.handle(B)
        assert "Cannot perform next: broken" in caplog.text

    def test_moc_server_is_started(self, controller, moc):
        moc.next.side_effect = MocServerNotRunningError("The server is not running!")
        controller.handle(B)
        moc.start_server.assert_called_once_with()

    def test_moc_server_cannot_be_started(self, controller, moc, caplog):
        moc.next.side_effect = MocServerNotRunningError("The server is not running!")
        moc.start_server.side_effect = MocError("Server exited!")
        with caplog.at_level(logging.ERROR):
            controller.handle(B)
        assert "Cannot perform next: Server exited!" in caplog.text

    def test_next(self, controller, moc):
        controller.handle(B)
        moc.next.assert_called_once_with()

    def test_open_menu(self, controller, state):
        controller.handle(A_LONG)
        assert state.mode == Mode.MENU
        assert [menu.title for menu in state.menus] == ["Menu"]

    def test_open_menu_replaces_the_open_menus(self, state, moc, library, system):
        button_map = resolve_button_map({"menu": {"A_long": "open_menu"}})
        controller = Controller(state, moc, library, system, button_map)
        controller.handle(A_LONG)
        controller.handle(B)
        controller.handle(A_LONG)
        assert [menu.title for menu in state.menus] == ["Menu"]

    def test_play_pause(self, controller, moc):
        controller.handle(A)
        moc.toggle_pause.assert_called_once_with()
        moc.play_playlist.assert_not_called()

    def test_play_pause_when_stopped(self, controller, state, moc):
        state.status = MocStatus(state=MocState.STOP)
        controller.handle(A)
        moc.play_playlist.assert_called_once_with()
        moc.toggle_pause.assert_not_called()

    def test_previous(self, controller, moc):
        controller.handle(B_LONG)
        moc.previous.assert_called_once_with()

    def test_seek(self, controller, moc):
        controller.handle(X_HOLD)
        moc.seek.assert_called_once_with(10)
        controller.handle(Y_HOLD)
        moc.seek.assert_called_with(-10)

    def test_seek_repeats_while_held(self, controller, moc):
        for event in (Y_LONG, Y_HOLD, Y_HOLD, Y_HOLD):
            controller.handle(event)
        assert [call.args for call in moc.seek.call_args_list] == [(-10,), (-10,), (-10,)]
        assert len(moc.mock_calls) == 3

    def test_unmapped_event(self, controller, state, moc):
        state.open_menu(Menu(title="Empty", items=()))
        controller.handle(B_LONG)
        assert moc.mock_calls == []
        assert state.current_menu.title == "Empty"

    def test_volume(self, controller, state, moc):
        controller.handle(X)
        assert state.volume == 55
        moc.set_volume.assert_called_with(55)
        controller.handle(Y)
        controller.handle(Y)
        assert state.volume == 45
        moc.set_volume.assert_called_with(45)

    def test_volume_is_clamped(self, controller, state, moc):
        state.volume = 98
        controller.handle(X)
        assert state.volume == 100
        moc.set_volume.assert_called_once_with(100)
