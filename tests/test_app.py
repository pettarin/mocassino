"""Tests for the application.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

import pytest

from mocassino.app import App, build_app
from mocassino.configuration import load_configuration
from mocassino.controller.actions import DEFAULT_BUTTON_MAP, Action
from mocassino.controller.buttons.gpio import GpioButtonSource
from mocassino.controller.buttons.null import NullButtonSource
from mocassino.controller.controller import Controller
from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.model.host import Host
from mocassino.model.library import Library
from mocassino.model.moc import (
    MocError,
    MocServerNotRunningError,
    MocState,
    MocStatus,
    SubprocessMocClient,
)
from mocassino.model.state import AppState, Mode
from mocassino.simulator.tk import TkSimulator
from mocassino.view.display.null import NullDisplay
from mocassino.view.display.st7789 import St7789Display
from mocassino.view.renderer import Renderer

PLAYING = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title="Title")
TICK = 0.01
# From playback mode: open the menu, go to Settings, open it, and select its first item
TOGGLE_SIDE_ICONS = (
    ButtonEvent(Button.A, Press.LONG),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.B),
    ButtonEvent(Button.B),
)


@pytest.fixture
def button_source(mocker):
    return mocker.create_autospec(NullButtonSource, instance=True)


@pytest.fixture
def display(mocker):
    return mocker.create_autospec(NullDisplay, instance=True)


@pytest.fixture
def moc(mocker):
    moc = mocker.create_autospec(SubprocessMocClient, instance=True)
    moc.status.return_value = PLAYING
    return moc


@pytest.fixture
def state():
    return AppState(volume=40)


@pytest.fixture
def app(mocker, tmp_path, state, moc, display, button_source):
    host = mocker.create_autospec(Host, instance=True)
    controller = Controller(
        state, moc, Library(tmp_path), host, DEFAULT_BUTTON_MAP, seek_step=10, volume_step=5
    )
    return App(state, controller, moc, Renderer(), display, button_source, tick=TICK)


class TestApp:
    """Tests for the App class"""

    def test_close(self, app, display, button_source):
        app.close()
        button_source.close.assert_called_once_with()
        display.close.assert_called_once_with()

    def test_run(self, app, moc, display, button_source):
        calls = []

        def status():
            calls.append(None)
            if len(calls) == 3:
                app.stop()
            return PLAYING

        moc.status.side_effect = status
        app.run()
        assert len(calls) == 3
        moc.start_server.assert_called_once_with()
        button_source.start.assert_called_once_with(app.events)
        button_source.close.assert_called_once_with()
        display.close.assert_called_once_with()

    def test_run_releases_the_hardware_on_errors(self, app, moc, display, button_source):
        moc.start_server.side_effect = MocError("Server exited!")
        with pytest.raises(MocError, match="Server exited!"):
            app.run()
        button_source.start.assert_not_called()
        button_source.close.assert_called_once_with()
        display.close.assert_called_once_with()

    def test_start(self, app, moc, button_source):
        app.start()
        moc.start_server.assert_called_once_with()
        moc.set_volume.assert_called_once_with(40)
        button_source.start.assert_called_once_with(app.events)

    def test_step_draws_only_changes(self, app, state, moc, display):
        app.step()
        assert state.status == PLAYING
        assert display.show.call_count == 1
        app.step()
        assert display.show.call_count == 1
        moc.status.return_value = MocStatus(state=MocState.STOP)
        app.step()
        assert display.show.call_count == 2
        image = display.show.call_args.args[0]
        assert image.size == (240, 240)

    def test_step_handles_all_the_events(self, app, state, moc, display):
        for _ in range(3):
            app.events.put(ButtonEvent(Button.X))
        app.events.put(ButtonEvent(Button.A, Press.LONG))
        app.step()
        assert state.volume == 55
        assert state.mode == Mode.MENU
        assert app.events.empty()
        assert moc.status.call_count == 1
        assert display.show.call_count == 1

    def test_step_logs_a_repeated_error_once(self, app, state, moc, caplog):
        moc.status.side_effect = MocError("broken")
        with caplog.at_level(logging.ERROR):
            app.step()
            app.step()
        assert caplog.text.count("Cannot get the MOC status: broken") == 1
        assert state.status == MocStatus()
        moc.status.side_effect = None
        app.step()
        assert state.status == PLAYING
        moc.status.side_effect = MocError("broken")
        with caplog.at_level(logging.ERROR):
            app.step()
        assert caplog.text.count("Cannot get the MOC status: broken") == 2

    def test_step_starts_the_moc_server(self, app, moc):
        moc.status.side_effect = MocServerNotRunningError("The server is not running!")
        app.step()
        moc.start_server.assert_called_once_with()

    def test_step_when_the_moc_server_cannot_be_started(self, app, moc, caplog):
        moc.status.side_effect = MocServerNotRunningError("The server is not running!")
        moc.start_server.side_effect = MocError("Server exited!")
        with caplog.at_level(logging.ERROR):
            app.step()
        assert "Cannot get the MOC status: Server exited!" in caplog.text


class TestBuildApp:
    """Tests for the build_app function"""

    @pytest.fixture(autouse=True)
    def home(self, tmp_path, monkeypatch):
        """Point the home directory to a temporary one, so the user's files are never read."""
        monkeypatch.setenv("HOME", str(tmp_path))

    def configuration(self, origin: str, target: str, **playback):
        return load_configuration(
            overrides={
                "buttons": {"origin": origin},
                "display": {"target": target},
                "playback": playback,
            }
        )

    @pytest.mark.parametrize(
        ("origin", "target"),
        [("gpio", "st7789"), ("pirateaudio", "pirateaudio")],
    )
    def test_hardware(self, mocker, origin, target):
        mocker.patch("st7789.ST7789")
        app = build_app(self.configuration(origin, target))
        assert isinstance(app._button_source, GpioButtonSource)
        assert isinstance(app._display, St7789Display)

    def test_no_hardware(self):
        app = build_app(self.configuration("none", "none", initial_volume=30, volume_step=10))
        assert isinstance(app._button_source, NullButtonSource)
        assert isinstance(app._display, NullDisplay)
        assert app.simulator is None
        assert app._state.volume == 30
        assert app._tick == 0.5
        app.events.put(ButtonEvent(Button.A, Press.LONG))
        app._controller.handle(app.events.get())
        assert app._state.mode == Mode.MENU

    def test_renderer_has_the_button_map(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"button_map": {"playback": {"A": "next"}}, "origin": "none"},
                "display": {"target": "none"},
            }
        )
        button_map = build_app(configuration)._renderer._button_map
        assert button_map[(Mode.PLAYBACK, ButtonEvent(Button.A))] == Action.NEXT

    def test_side_icons_setting(self):
        shown = build_app(self.configuration("none", "none"))
        assert shown._state.settings.show_side_icons is True
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"show_side_icons": False, "target": "none"},
            }
        )
        assert build_app(configuration)._state.settings.show_side_icons is False

    def test_settings_are_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("playback:\n  initial_volume: 30\n", encoding="utf-8")
        configuration = load_configuration(
            path,
            {"buttons": {"origin": "none"}, "display": {"target": "none"}},
        )
        app = build_app(configuration, path)
        for event in TOGGLE_SIDE_ICONS:
            app._controller.handle(event)
        assert app._state.settings.show_side_icons is False
        assert path.read_text(encoding="utf-8") == (
            "playback:\n  initial_volume: 30\ndisplay:\n  show_side_icons: false\n"
        )
        assert load_configuration(path).display.show_side_icons is False

    def test_settings_are_saved_to_the_default_file(self, tmp_path):
        app = build_app(self.configuration("none", "none"))
        for event in TOGGLE_SIDE_ICONS:
            app._controller.handle(event)
        path = tmp_path / ".config" / "mocassino" / "configuration.yaml"
        assert path.read_text(encoding="utf-8") == "display:\n  show_side_icons: false\n"

    def test_settings_cannot_be_saved(self, tmp_path, caplog):
        blocker = tmp_path / "blocker"
        blocker.touch()
        app = build_app(self.configuration("none", "none"), blocker / "configuration.yaml")
        with caplog.at_level(logging.ERROR):
            for event in TOGGLE_SIDE_ICONS:
                app._controller.handle(event)
        assert "Cannot save the settings: Cannot write configuration file" in caplog.text
        assert app._state.settings.show_side_icons is False
        assert app._state.current_menu.selected.label == "Side icons: off"

    def test_simulator(self):
        app = build_app(self.configuration("simulator", "simulator"))
        assert isinstance(app.simulator, TkSimulator)
        assert app._button_source is app.simulator
        assert app._display is app.simulator

    def test_simulator_for_the_buttons_only(self):
        app = build_app(self.configuration("simulator", "none"))
        assert app._button_source is app.simulator
        assert isinstance(app._display, NullDisplay)

    def test_simulator_for_the_display_only(self):
        app = build_app(self.configuration("none", "simulator"))
        assert isinstance(app._button_source, NullButtonSource)
        assert app._display is app.simulator
