"""Tests for the controller.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.controller.actions import DEFAULT_BUTTON_MAP, resolve_button_map
from mocassino.controller.controller import Controller
from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.model.host import Host, HostError
from mocassino.model.library import Library
from mocassino.model.menu import Menu, MenuCommand, MenuItem
from mocassino.model.moc import (
    MocError,
    MocServerNotRunningError,
    MocState,
    MocStatus,
    SubprocessMocClient,
)
from mocassino.model.state import AppState, Mode

A = ButtonEvent(Button.A)
A_LONG = ButtonEvent(Button.A, Press.LONG)
B = ButtonEvent(Button.B)
B_LONG = ButtonEvent(Button.B, Press.LONG)
X = ButtonEvent(Button.X)
X_HOLD = ButtonEvent(Button.X, Press.HOLD)
X_LONG = ButtonEvent(Button.X, Press.LONG)
Y = ButtonEvent(Button.Y)
Y_HOLD = ButtonEvent(Button.Y, Press.HOLD)
Y_LONG = ButtonEvent(Button.Y, Press.LONG)


@pytest.fixture
def host(mocker):
    host = mocker.create_autospec(Host, instance=True)
    host.hostname.return_value = "pirate"
    host.ip_address.return_value = "192.168.1.20"
    return host


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
def controller(state, moc, library, host):
    return Controller(state, moc, library, host, DEFAULT_BUTTON_MAP, seek_step=10, volume_step=5)


def open_single_item_menu(state, item) -> None:
    """Open a menu having only the given item, on top of another menu."""
    state.open_menu(Menu(title="Below", items=()))
    state.open_menu(Menu(title="Above", items=(item,)))


class TestController:
    """Tests for the Controller class"""

    def test_custom_button_map(self, state, moc, library, host):
        button_map = {"playback": {"X_long": "next"}}
        controller = Controller(state, moc, library, host, button_map, seek_step=10, volume_step=5)
        controller.handle(X_LONG)
        moc.next.assert_called_once_with()
        controller.handle(A)
        moc.toggle_pause.assert_not_called()

    def test_host_error_is_logged(self, controller, state, host, caplog):
        host.shutdown.side_effect = HostError("denied")
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        with caplog.at_level(logging.ERROR):
            controller.handle(B)
        assert "Cannot perform menu_select: denied" in caplog.text

    def test_invalid_button_map(self, state, moc, library, host):
        with pytest.raises(ValueError, match="is not a valid"):
            Controller(
                state, moc, library, host, {"menu": {"A": "rewind"}}, seek_step=10, volume_step=5
            )

    def test_menu_actions_without_menu(self, state, moc, library, host):
        button_map = {"playback": {"A": "menu_select", "B": "menu_back", "X": "menu_up"}}
        controller = Controller(state, moc, library, host, button_map, seek_step=10, volume_step=5)
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
        assert menu.selected.label == "Back to playback"

    def test_menu_select_back(self, controller, state):
        open_single_item_menu(state, MenuItem(label="Cancel", command=MenuCommand.BACK))
        controller.handle(B)
        assert state.current_menu.title == "Below"

    @pytest.mark.parametrize("event", [B, X_LONG, Y_LONG])
    def test_menu_select_buttons(self, controller, state, event):
        controller.handle(A_LONG)
        controller.handle(event)
        assert [menu.title for menu in state.menus] == ["Menu", "Library"]

    def test_menu_select_close(self, controller, state):
        open_single_item_menu(state, MenuItem(label="Close", command=MenuCommand.CLOSE))
        controller.handle(B)
        assert state.mode == Mode.PLAYBACK

    def test_menu_select_empty_menu(self, controller, state):
        state.open_menu(Menu(title="Empty", items=()))
        controller.handle(B)
        assert state.current_menu.title == "Empty"

    def test_menu_select_information(self, controller, state, moc, host):
        open_single_item_menu(state, MenuItem(label="Name: pirate"))
        controller.handle(B)
        assert state.current_menu.title == "Above"
        assert moc.mock_calls == []
        host.shutdown.assert_not_called()

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

    def test_menu_select_shutdown(self, controller, state, host):
        controller.handle(A_LONG)
        controller.handle(Y)
        controller.handle(Y)
        controller.handle(B)
        assert state.current_menu.title == "Host"
        controller.handle(X)
        controller.handle(B)
        assert state.current_menu.title == "Shut down?"
        host.shutdown.assert_not_called()
        controller.handle(Y)
        controller.handle(B)
        host.shutdown.assert_called_once_with()
        assert state.mode == Mode.PLAYBACK
        assert state.shutting_down is True

    def test_menu_select_shutdown_is_flagged_before_it_is_asked(self, controller, state, host):
        flags = []
        host.shutdown.side_effect = lambda: flags.append(state.shutting_down)
        open_single_item_menu(state, MenuItem(label="Off", command=MenuCommand.SHUTDOWN))
        assert state.shutting_down is False
        controller.handle(B)
        assert flags == [True]

    def test_menu_select_toggle_side_icons(self, controller, state):
        controller.handle(A_LONG)
        controller.handle(Y)
        controller.handle(B)
        assert state.current_menu.title == "Settings"
        assert state.current_menu.selected.label == "Side icons"
        assert state.current_menu.selected.checked is True
        controller.handle(B)
        assert state.settings.show_side_icons is False
        assert [menu.title for menu in state.menus] == ["Menu", "Settings"]
        assert state.current_menu.selected.checked is False
        controller.handle(B)
        assert state.settings.show_side_icons is True
        assert state.current_menu.selected.checked is True
        controller.handle(A)
        controller.handle(B)
        assert state.current_menu.selected.checked is True

    def test_menu_select_toggle_side_icons_saves_the_settings(
        self, mocker, state, moc, library, host
    ):
        save_settings = mocker.Mock()
        controller = Controller(
            state,
            moc,
            library,
            host,
            DEFAULT_BUTTON_MAP,
            seek_step=10,
            volume_step=5,
            save_settings=save_settings,
        )
        for event in (A_LONG, Y, B):
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

    def test_open_menu_replaces_the_open_menus(self, state, moc, library, host):
        button_map = resolve_button_map({"menu": {"A_long": "open_menu"}})
        controller = Controller(state, moc, library, host, button_map, seek_step=10, volume_step=5)
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
