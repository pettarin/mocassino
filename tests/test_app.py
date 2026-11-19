"""Tests for the application.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import subprocess
from dataclasses import replace

import pytest

from mocassino.app import App, build_app
from mocassino.configuration import Configuration, load_configuration
from mocassino.controller.actions import DEFAULT_BUTTON_MAP, Action
from mocassino.controller.buttons.gpio import GpioButtonSource
from mocassino.controller.buttons.null import NullButtonSource
from mocassino.controller.controller import Controller
from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.model.library import Library
from mocassino.model.moc import (
    MocError,
    MocServerNotRunningError,
    MocState,
    MocStatus,
    SubprocessMocClient,
)
from mocassino.model.settings import (
    MocStateOnExit,
    Settings,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.model.state import AppState, Mode
from mocassino.model.state_file import SavedState, StateFile
from mocassino.model.system import System, SystemShutdownError
from mocassino.simulator.tk import TkSimulator
from mocassino.view.display.null import NullDisplay
from mocassino.view.display.st7789 import St7789Display
from mocassino.view.renderer import Renderer
from tests.model.fake_moc import FakeMoc

PLAYING = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title="Title")
# From playback mode: open the menu, go up to System, open it, go up to Shut down,
# open it, go down to Shut down now, and select it
SHUT_DOWN = (
    ButtonEvent(Button.A, Press.LONG),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.B),
)
# From playback mode: open the menu, go up to System, open it, go up twice to Reboot,
# open it, go down to Reboot now, and select it
REBOOT = (
    ButtonEvent(Button.A, Press.LONG),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.X),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.B),
)
# From playback mode: open the menu, go up to System, open it, go up thrice to Reset settings,
# open it, go down to Reset now, and select it
RESET_SETTINGS = (
    ButtonEvent(Button.A, Press.LONG),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.X),
    ButtonEvent(Button.X),
    ButtonEvent(Button.X),
    ButtonEvent(Button.B),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.B),
)
TICK = 0.01
# From playback mode: open the menu, go to Settings, open it, open Display (its first item),
# go to Show side icons (its third item), and select it
TOGGLE_SIDE_ICONS = (
    ButtonEvent(Button.A, Press.LONG),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.B),
    ButtonEvent(Button.B),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.Y),
    ButtonEvent(Button.Y),
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
    system = mocker.create_autospec(System, instance=True)
    controller = Controller(state, moc, Library(tmp_path), system, DEFAULT_BUTTON_MAP)
    return App(state, controller, moc, Renderer(), display, button_source, tick=TICK)


@pytest.fixture
def state_file(mocker):
    state_file = mocker.create_autospec(StateFile, instance=True)
    state_file.load.return_value = SavedState()
    return state_file


@pytest.fixture
def saving_app(mocker, tmp_path, state, moc, display, button_source, state_file):
    """An application with a state file."""
    system = mocker.create_autospec(System, instance=True)
    controller = Controller(state, moc, Library(tmp_path), system, DEFAULT_BUTTON_MAP)
    return App(
        state, controller, moc, Renderer(), display, button_source, TICK, state_file=state_file
    )


class TestApp:
    """Tests for the App class"""

    def test_state_is_saved(self, saving_app, state_file, moc):
        app = saving_app
        playing = SavedState(
            directory_path="/music", file_path="/music/a.flac", state=MocState.PLAY, volume=40
        )
        app.step()
        state_file.save.assert_called_once_with(playing)
        app.step()
        assert state_file.save.call_count == 1
        app.events.put(ButtonEvent(Button.X))
        app.step()
        state_file.save.assert_called_with(replace(playing, volume=45))
        assert state_file.save.call_count == 2
        moc.status.return_value = MocStatus(
            current_seconds=7, file_path="/music/b.flac", state=MocState.PAUSE
        )
        app.step()
        assert state_file.save.call_count == 3
        state_file.save.assert_called_with(
            replace(playing, file_path="/music/b.flac", seek=7, state=MocState.PAUSE, volume=45)
        )
        for event in TOGGLE_SIDE_ICONS:
            app.events.put(event)
        app.step()
        assert state_file.save.call_count == 4
        app.step()
        assert state_file.save.call_count == 4
        moc.status.return_value = MocStatus(
            current_seconds=60, file_path="/music/b.flac", state=MocState.PAUSE
        )
        app.step()
        assert state_file.save.call_count == 4
        app.close()
        assert state_file.save.call_count == 5
        state_file.save.assert_called_with(
            replace(playing, file_path="/music/b.flac", seek=60, state=MocState.PAUSE, volume=45)
        )

    def test_state_saved_has_the_played_path(self, saving_app, state_file, state):
        state.played_path = "/music"
        saving_app.step()
        state_file.save.assert_called_once_with(
            SavedState(
                directory_path="/music",
                file_path="/music/a.flac",
                state=MocState.PLAY,
                volume=40,
            )
        )

    def test_state_saved_has_the_directory_of_the_track_when_played_from_elsewhere(
        self, saving_app, state_file, state, moc
    ):
        state.played_path = "/music/Other"
        moc.status.return_value = MocStatus(file_path="/music/Album/03.flac", state=MocState.PLAY)
        saving_app.step()
        state_file.save.assert_called_once_with(
            SavedState(
                directory_path="/music/Album",
                file_path="/music/Album/03.flac",
                state=MocState.PLAY,
                volume=40,
            )
        )

    def test_state_saved_of_a_stream_has_no_directory(self, saving_app, state_file, moc):
        moc.status.return_value = MocStatus(
            file_path="http://example.com/stream", state=MocState.PLAY
        )
        saving_app.step()
        state_file.save.assert_called_once_with(
            SavedState(file_path="http://example.com/stream", state=MocState.PLAY, volume=40)
        )

    def test_state_saved_is_blank_when_stopped(self, saving_app, state_file, state, moc):
        state.played_path = "/music"
        saving_app.step()
        moc.status.return_value = MocStatus(state=MocState.STOP)
        saving_app.step()
        state_file.save.assert_called_with(SavedState(volume=40))

    def test_state_is_kept_as_saved_when_shutting_down(self, saving_app, state_file, state, moc):
        app = saving_app
        state.played_path = "/music"
        app.step()
        assert state_file.save.call_count == 1
        moc.status.return_value = MocStatus(
            current_seconds=33, file_path="/music/a.flac", state=MocState.PLAY
        )
        app.step()
        state.shutting_down = True
        moc.status.return_value = MocStatus(state=MocState.STOP)
        app.step()
        assert state_file.save.call_count == 2
        state_file.save.assert_called_with(
            SavedState(
                directory_path="/music",
                file_path="/music/a.flac",
                seek=33,
                state=MocState.PLAY,
                volume=40,
            )
        )
        app.step()
        app.close()
        assert state_file.save.call_count == 2

    def test_start_resumes_the_saved_playback(self, saving_app, state_file, state, moc, mocker):
        saved = SavedState(directory_path="/music", file_path="/music/a.flac", volume=40)
        state_file.load.return_value = saved
        resume = mocker.patch("mocassino.app.resume_playback", return_value="/music")
        order = mocker.Mock()
        order.attach_mock(moc.stop, "stop")
        order.attach_mock(resume, "resume")
        order.attach_mock(moc.set_volume, "set_volume")
        saving_app.start()
        resume.assert_called_once_with(moc, saved)
        assert [call[0] for call in order.mock_calls] == ["stop", "resume", "set_volume"]
        moc.set_volume.assert_called_once_with(40)
        assert state.played_path == "/music"
        state_file.save.assert_called_once_with(
            SavedState(
                directory_path="/music",
                file_path="/music/a.flac",
                state=MocState.PLAY,
                volume=40,
            )
        )

    def test_start_using_the_moc_state(self, saving_app, state_file, state, moc, mocker):
        state.settings.startup_playlist = StartupPlaylist.USE_MOC_STATE
        saved = SavedState(directory_path="/music", file_path="/music/z.flac", volume=40)
        state_file.load.return_value = saved
        resume = mocker.patch("mocassino.app.resume_playback")
        saving_app.start()
        moc.stop.assert_not_called()
        resume.assert_not_called()
        assert state.played_path == "/music"
        assert state.mode == Mode.PLAYBACK
        assert state.status == PLAYING
        moc.set_volume.assert_called_once_with(40)
        state_file.save.assert_called_once_with(
            SavedState(
                directory_path="/music",
                file_path="/music/a.flac",
                state=MocState.PLAY,
                volume=40,
            )
        )

    def test_start_using_the_moc_state_when_moc_plays_something_else(
        self, saving_app, state_file, state, moc
    ):
        state.settings.startup_playlist = StartupPlaylist.USE_MOC_STATE
        state_file.load.return_value = SavedState(
            directory_path="/other", file_path="/other/z.flac", volume=40
        )
        saving_app.start()
        moc.stop.assert_not_called()
        assert state.played_path == "/music"
        assert state.status == PLAYING

    def test_start_selecting_from_the_library(self, saving_app, state_file, state, moc, mocker):
        state.settings.startup_playlist = StartupPlaylist.OPEN_LIBRARY
        state_file.load.return_value = SavedState(
            directory_path="/music", file_path="/music/a.flac", state=MocState.PLAY, volume=40
        )
        resume = mocker.patch("mocassino.app.resume_playback")
        moc.stop.side_effect = lambda: setattr(moc.status, "return_value", MocStatus())
        saving_app.start()
        moc.stop.assert_called_once_with()
        resume.assert_not_called()
        assert [menu.title for menu in state.menus] == ["Menu", "Library"]
        assert state.played_path is None
        moc.set_volume.assert_called_once_with(40)
        state_file.save.assert_called_once_with(SavedState(volume=40))

    def test_start_without_state_file(self, app, state, moc, mocker):
        resume = mocker.patch("mocassino.app.resume_playback", return_value=None)
        app.start()
        moc.stop.assert_called_once_with()
        resume.assert_called_once_with(moc, SavedState())
        assert state.played_path is None

    def test_start_when_nothing_can_be_resumed(self, saving_app, state_file, state, moc, mocker):
        state_file.load.return_value = SavedState(
            directory_path="/gone", file_path="/gone/a.flac", state=MocState.PLAY, volume=40
        )
        mocker.patch("mocassino.app.resume_playback", return_value=None)
        moc.status.return_value = MocStatus(state=MocState.STOP)
        saving_app.start()
        assert state.played_path is None
        state_file.save.assert_called_once_with(SavedState(volume=40))

    def test_start_when_resuming_fails(self, saving_app, state_file, moc, mocker, caplog):
        mocker.patch("mocassino.app.resume_playback", side_effect=MocError("broken"))
        moc.status.return_value = MocStatus(state=MocState.STOP)
        with caplog.at_level(logging.ERROR):
            saving_app.start()
        assert "Cannot set up the playlist: broken" in caplog.text
        moc.set_volume.assert_called_once_with(40)
        state_file.save.assert_called_once_with(SavedState(volume=40))

    def test_close(self, app, moc, display, button_source):
        app.close()
        button_source.close.assert_called_once_with()
        display.close.assert_called_once_with()
        moc.pause.assert_not_called()
        moc.stop.assert_not_called()
        moc.exit_server.assert_not_called()

    @pytest.mark.parametrize(
        ("choice", "command"),
        [
            (MocStateOnExit.PAUSE, "pause"),
            (MocStateOnExit.QUIT, "exit_server"),
            (MocStateOnExit.STOP, "stop"),
        ],
    )
    def test_close_leaves_moc(self, mocker, saving_app, state, moc, state_file, choice, command):
        state.settings.system_moc_state_on_exit = choice
        calls = mocker.Mock()
        state_file.save.side_effect = calls.save
        getattr(moc, command).side_effect = calls.leave
        saving_app.close()
        assert [call[0] for call in calls.mock_calls] == ["save", "leave"]
        others = {"pause", "stop", "exit_server"} - {command}
        assert all(not getattr(moc, other).called for other in others)

    def test_close_leaves_moc_despite_errors(self, app, state, moc, display, button_source, caplog):
        state.settings.system_moc_state_on_exit = MocStateOnExit.QUIT
        moc.exit_server.side_effect = MocError("not running")
        with caplog.at_level(logging.ERROR):
            app.close()
        assert "Cannot quit MOC on exit: not running" in caplog.text
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

    def test_step_sets_the_brightness_only_when_changed(self, app, state, display):
        app.step()
        display.set_brightness.assert_not_called()
        state.settings.display_brightness = 20
        app.step()
        app.step()
        display.set_brightness.assert_called_once_with(0.2)

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
        backlight_class = mocker.patch("gpiozero.PWMOutputDevice")
        mocker.patch("st7789.ST7789")
        configuration = self.configuration(origin, target)
        configuration = replace(
            configuration,
            display=replace(configuration.display, brightness=0.3),
        )
        app = build_app(configuration)
        assert isinstance(app._button_source, GpioButtonSource)
        assert isinstance(app._display, St7789Display)
        assert backlight_class.call_args.kwargs["initial_value"] == 0.3
        assert app._state.settings.display_brightness == 30

    def test_colors_from_the_configuration(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"colors": {"background": "#00F", "muted": "Red"}, "target": "none"},
            }
        )
        app = build_app(configuration)
        settings = app._state.settings
        assert settings.display_colors_background == "#00F"
        assert settings.display_colors_muted == "Red"
        assert settings.display_colors_accented == "limegreen"
        image = app._renderer.render(app._state)
        assert image.getpixel((1, 1)) == (0, 0, 255)

    def test_no_hardware(self):
        app = build_app(self.configuration("none", "none", volume_default=30, volume_step=10))
        assert isinstance(app._button_source, NullButtonSource)
        assert isinstance(app._display, NullDisplay)
        assert app.simulator is None
        assert app._state.volume == 30
        assert app._tick == 0.5
        app.events.put(ButtonEvent(Button.A, Press.LONG))
        app._controller.handle(app.events.get())
        assert app._state.mode == Mode.MENU

    def test_playback_steps_from_the_configuration(self, mocker):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        app = build_app(self.configuration("none", "none", seek_step=30, volume_step=4))
        assert app._state.settings.playback_seek_step == 30
        assert app._state.settings.playback_volume_step == 4
        app._controller.handle(ButtonEvent(Button.X))
        moc.set_volume.assert_called_once_with(54)
        app._controller.handle(ButtonEvent(Button.X, Press.HOLD))
        moc.seek.assert_called_once_with(30)

    def test_playback_steps_settings_are_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        titles = ["Menu", "Settings", "Playback", "Seek step (s)"]
        assert [menu.title for menu in app._state.menus] == titles
        assert app._state.settings.playback_seek_step == 30
        assert load_configuration(path).playback.seek_step == 30
        assert load_configuration(path).playback.volume_step == 5

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
        path.write_text("playback:\n  volume_default: 30\n", encoding="utf-8")
        configuration = load_configuration(
            path,
            {"buttons": {"origin": "none"}, "display": {"target": "none"}},
        )
        app = build_app(configuration, path)
        for event in TOGGLE_SIDE_ICONS:
            app._controller.handle(event)
        assert app._state.settings.show_side_icons is False
        assert path.read_text(encoding="utf-8") == (
            "playback:\n"
            "  volume_default: 30\n"
            "  seek_step: 10\n"
            "  volume_step: 5\n"
            "display:\n"
            "  brightness: 1.0\n"
            "  colors:\n"
            "    accented: limegreen\n"
            "    background: black\n"
            "    muted: silver\n"
            "    normal: white\n"
            "    track: dimgray\n"
            "  orientation: 0\n"
            "  show_progress_bar: true\n"
            "  show_side_icons: false\n"
            "  show_volume_bar: true\n"
            "startup:\n"
            "  playlist: use_saved\n"
            "  state: use_saved\n"
            "  volume: use_saved\n"
            "system:\n"
            "  moc_state_on_exit: do_nothing\n"
        )
        assert load_configuration(path).display.show_side_icons is False

    def test_settings_are_saved_to_the_default_file(self, tmp_path):
        app = build_app(self.configuration("none", "none"))
        for event in TOGGLE_SIDE_ICONS:
            app._controller.handle(event)
        path = tmp_path / ".config" / "mocassino" / "configuration.yaml"
        assert path.read_text(encoding="utf-8") == (
            "display:\n"
            "  brightness: 1.0\n"
            "  colors:\n"
            "    accented: limegreen\n"
            "    background: black\n"
            "    muted: silver\n"
            "    normal: white\n"
            "    track: dimgray\n"
            "  orientation: 0\n"
            "  show_progress_bar: true\n"
            "  show_side_icons: false\n"
            "  show_volume_bar: true\n"
            "playback:\n"
            "  seek_step: 10\n"
            "  volume_default: 50\n"
            "  volume_step: 5\n"
            "startup:\n"
            "  playlist: use_saved\n"
            "  state: use_saved\n"
            "  volume: use_saved\n"
            "system:\n"
            "  moc_state_on_exit: do_nothing\n"
        )

    def test_settings_cannot_be_saved(self, tmp_path, caplog):
        blocker = tmp_path / "blocker"
        blocker.touch()
        app = build_app(self.configuration("none", "none"), blocker / "configuration.yaml")
        with caplog.at_level(logging.ERROR):
            for event in TOGGLE_SIDE_ICONS:
                app._controller.handle(event)
        assert "Cannot save the settings: Cannot write configuration file" in caplog.text
        assert app._state.settings.show_side_icons is False
        assert app._state.current_menu.selected.checked is False

    def test_volume_from_the_configuration(self, tmp_path):
        state_file_path = tmp_path / "state.yaml"
        app = build_app(
            self.configuration("none", "none", volume_default=30),
            state_file_path=state_file_path,
        )
        assert app._state.volume == 30
        assert not state_file_path.exists()
        app.close()
        assert StateFile(state_file_path).load() == SavedState(volume=30)

    def test_volume_from_the_default_state_file(self, tmp_path):
        directory = tmp_path / ".config" / "mocassino"
        directory.mkdir(parents=True)
        (directory / "state.yaml").write_text("playback:\n  volume: 85\n", encoding="utf-8")
        app = build_app(self.configuration("none", "none", volume_default=30))
        assert app._state.volume == 85

    def test_volume_from_the_state_file(self, mocker, tmp_path):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        moc.status.return_value = PLAYING
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text("playback:\n  volume: 85\n", encoding="utf-8")
        app = build_app(
            self.configuration("none", "none", volume_default=30, volume_step=5),
            state_file_path=state_file_path,
        )
        assert app._state.volume == 85
        app.start()
        moc.set_volume.assert_called_once_with(85)
        app.events.put(ButtonEvent(Button.Y))
        app.step()
        moc.set_volume.assert_called_with(80)
        assert StateFile(state_file_path).load() == SavedState(
            directory_path="/music",
            file_path=PLAYING.file_path,
            state=MocState.PLAY,
            volume=80,
        )

    def test_volume_from_the_state_file_not_used(self, tmp_path):
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text("playback:\n  volume: 85\n", encoding="utf-8")
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"target": "none"},
                "playback": {"volume_default": 30},
                "startup": {"volume": "use_default"},
            }
        )
        app = build_app(configuration, state_file_path=state_file_path)
        assert app._state.volume == 30
        assert app._state.settings.startup_volume is StartupVolume.USE_DEFAULT

    def test_startup_playlist_from_the_configuration(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"target": "none"},
                "startup": {"playlist": "open_library"},
            }
        )
        app = build_app(configuration)
        assert app._state.settings.startup_playlist is StartupPlaylist.OPEN_LIBRARY
        default = build_app(self.configuration("none", "none"))
        assert default._state.settings.startup_playlist is StartupPlaylist.USE_SAVED

    def test_startup_playlist_setting_is_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.startup_playlist is StartupPlaylist.USE_MOC_STATE
        assert load_configuration(path).startup.playlist == "use_moc_state"

    def test_display_bars_from_the_configuration(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {
                    "show_progress_bar": False,
                    "show_volume_bar": False,
                    "target": "none",
                },
            }
        )
        settings = build_app(configuration)._state.settings
        assert (settings.show_progress_bar, settings.show_volume_bar) == (False, False)
        assert settings.show_side_icons is True
        default = build_app(self.configuration("none", "none"))._state.settings
        assert (default.show_progress_bar, default.show_volume_bar) == (True, True)

    def test_display_bars_settings_are_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.show_progress_bar is False
        assert app._state.settings.show_volume_bar is False
        saved = load_configuration(path).display
        assert (saved.show_progress_bar, saved.show_side_icons, saved.show_volume_bar) == (
            False,
            True,
            False,
        )

    def test_moc_state_on_exit_from_the_configuration_and_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"target": "none"},
                "system": {"moc_state_on_exit": "pause"},
            }
        )
        app = build_app(configuration, path)
        assert app._state.settings.system_moc_state_on_exit is MocStateOnExit.PAUSE
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.system_moc_state_on_exit is MocStateOnExit.STOP
        assert load_configuration(path).system.moc_state_on_exit == "stop"

    def test_display_brightness_from_the_configuration(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"brightness": 0.42, "target": "none"},
            }
        )
        assert build_app(configuration)._state.settings.display_brightness == 42

    def test_display_color_setting_is_applied_and_saved(self, mocker, tmp_path):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        moc.status.return_value = PLAYING
        path = tmp_path / "custom.yaml"
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"colors": {"muted": "#123456"}, "target": "none"},
            }
        )
        app = build_app(configuration, path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
        )
        for event in events:
            app.events.put(event)
        app.step()
        assert app._state.settings.display_colors_accented == "linen"
        assert app._renderer._colors.accented == (250, 240, 230)
        saved = load_configuration(path).display.colors
        assert (saved.accented, saved.muted, saved.track) == ("linen", "#123456", "dimgray")

    def test_display_brightness_setting_is_applied_and_saved(self, mocker, tmp_path):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        moc.status.return_value = PLAYING
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.X),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
        )
        for event in events:
            app.events.put(event)
        assert app._display.brightness == 1.0
        app.step()
        assert app._state.settings.display_brightness == 85
        assert app._display.brightness == 0.85
        assert load_configuration(path).display.brightness == 0.85

    def test_display_orientation_from_the_configuration(self):
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"orientation": 180, "target": "none"},
            }
        )
        assert build_app(configuration)._state.settings.display_orientation == 180
        default = build_app(self.configuration("none", "none"))
        assert default._state.settings.display_orientation == 0

    def test_display_orientation_setting_is_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.display_orientation == 270
        assert load_configuration(path).display.orientation == 270

    def test_playback_volume_default_setting_is_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none", volume_default=30), path)
        assert app._state.settings.playback_volume_default == 30
        assert app._state.volume == 30
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.current_menu.selected.label == "35"
        assert app._state.settings.playback_volume_default == 35
        assert app._state.volume == 30
        assert load_configuration(path).playback.volume_default == 35

    def test_startup_volume_setting_is_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        assert app._state.settings.startup_volume is StartupVolume.USE_SAVED
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.startup_volume is StartupVolume.USE_DEFAULT
        assert load_configuration(path).startup.volume == "use_default"
        assert load_configuration(path).display.show_side_icons is True

    def test_volume_from_the_state_file_not_valid(self, tmp_path):
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text("playback:\n  volume: 850\n", encoding="utf-8")
        app = build_app(
            self.configuration("none", "none", volume_default=30),
            state_file_path=state_file_path,
        )
        assert app._state.volume == 30

    def test_playback_is_saved_and_resumed(self, mocker, tmp_path):
        album = tmp_path / "music" / "Album"
        album.mkdir(parents=True)
        for number in range(1, 6):
            (album / f"0{number}.flac").touch()
        moc = FakeMoc()
        mocker.patch("mocassino.app.SubprocessMocClient", return_value=moc)
        mocker.patch("mocassino.model.resume.time.sleep")
        state_file_path = tmp_path / "state.yaml"
        configuration = self.configuration("none", "none", volume_default=30)
        app = build_app(configuration, state_file_path=state_file_path)
        app.start()
        assert moc.state is MocState.STOP
        assert StateFile(state_file_path).load() == SavedState(volume=30)
        moc.play(album)
        app._state.played_path = str(album)
        moc.next()
        moc.next()
        moc.jump(95)
        moc.pause()
        app.step()
        app.close()
        saved = SavedState(
            directory_path=str(album),
            file_path=str(album / "03.flac"),
            seek=95,
            state=MocState.PAUSE,
            volume=30,
        )
        assert StateFile(state_file_path).load() == saved
        moc = FakeMoc()
        mocker.patch("mocassino.app.SubprocessMocClient", return_value=moc)
        app = build_app(configuration, state_file_path=state_file_path)
        app.start()
        assert (moc.index, moc.seconds, moc.state) == (2, 95, MocState.PAUSE)
        assert moc.volume == 30
        assert moc.names()[:3] == ["start_server", "stop", "set_volume"]
        assert moc.names()[-1] == "set_volume"
        assert app._state.played_path == str(album)
        assert StateFile(state_file_path).load() == saved

    def test_playback_saved_without_directory_is_resumed(self, mocker, tmp_path):
        """A state file with the track but no directory: the directory of the track is played."""
        album = tmp_path / "music" / "Polvere"
        album.mkdir(parents=True)
        for number in range(1, 6):
            (album / f"00{number}.flac").touch()
        moc = FakeMoc()
        mocker.patch("mocassino.app.SubprocessMocClient", return_value=moc)
        mocker.patch("mocassino.model.resume.time.sleep")
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text(
            "playback:\n"
            "  directory_path: null\n"
            f"  file_path: {album / '003.flac'}\n"
            "  seek: 5\n"
            "  state: playing\n"
            "  volume: 90\n",
            encoding="utf-8",
        )
        app = build_app(self.configuration("none", "none"), state_file_path=state_file_path)
        app.start()
        assert moc.names()[:2] == ["start_server", "stop"]
        assert (moc.index, moc.seconds, moc.state) == (2, 5, MocState.PLAY)
        assert moc.volume == 90
        assert StateFile(state_file_path).load() == SavedState(
            directory_path=str(album),
            file_path=str(album / "003.flac"),
            seek=5,
            state=MocState.PLAY,
            volume=90,
        )

    @pytest.fixture
    def album(self, tmp_path):
        """Create an album of five tracks."""
        album = tmp_path / "music" / "Album"
        album.mkdir(parents=True)
        for number in range(1, 6):
            (album / f"0{number}.flac").touch()
        return album

    def start(self, mocker, tmp_path, album, playlist, state, saved_state, moc=None):
        """Start an application with the given startup settings, and a saved track 3 at 95 s."""
        moc = moc or FakeMoc()
        mocker.patch("mocassino.app.SubprocessMocClient", return_value=moc)
        mocker.patch("mocassino.model.resume.time.sleep")
        state_file_path = tmp_path / "state.yaml"
        StateFile(state_file_path).save(
            SavedState(
                directory_path=str(album),
                file_path=str(album / "03.flac"),
                seek=95,
                state=saved_state,
                volume=70,
            )
        )
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"target": "none"},
                "startup": {"playlist": playlist, "state": state},
            }
        )
        app = build_app(configuration, state_file_path=state_file_path)
        app.start()
        return app, moc

    @pytest.mark.parametrize(
        ("state", "saved_state", "expected"),
        [
            ("use_saved", MocState.PLAY, MocState.PLAY),
            ("use_saved", MocState.PAUSE, MocState.PAUSE),
            ("play", MocState.PAUSE, MocState.PLAY),
            ("play", MocState.PLAY, MocState.PLAY),
            ("pause", MocState.PLAY, MocState.PAUSE),
            ("pause", MocState.PAUSE, MocState.PAUSE),
        ],
    )
    def test_startup_state_with_the_saved_playlist(
        self, mocker, tmp_path, album, state, saved_state, expected
    ):
        app, moc = self.start(mocker, tmp_path, album, "use_saved", state, saved_state)
        assert (moc.index, moc.seconds, moc.state) == (2, 95, expected)
        assert moc.volume == 70
        assert app._state.played_path == str(album)
        assert app._state.settings.startup_state is StartupState(state)

    @pytest.mark.parametrize("saved_state", [MocState.PLAY, MocState.PAUSE])
    def test_startup_state_stop_with_the_saved_playlist(self, mocker, tmp_path, album, saved_state):
        app, moc = self.start(mocker, tmp_path, album, "use_saved", "stop", saved_state)
        assert moc.names() == ["start_server", "stop", "load", "set_volume"]
        assert moc.state is MocState.STOP
        assert len(moc.tracks) == 5
        assert app._state.played_path == str(album)
        assert app._state.status.state is MocState.STOP

    @pytest.mark.parametrize(
        ("state", "commands", "expected"),
        [
            ("use_saved", [], MocState.PLAY),
            ("play", [], MocState.PLAY),
            ("pause", ["pause"], MocState.PAUSE),
            ("stop", ["stop"], MocState.STOP),
        ],
    )
    def test_startup_state_with_the_moc_state(
        self, mocker, tmp_path, album, state, commands, expected
    ):
        moc = FakeMoc()
        moc.play(album)
        moc.next()
        moc.calls.clear()
        app, moc = self.start(
            mocker, tmp_path, album, "use_moc_state", state, MocState.PAUSE, moc=moc
        )
        assert moc.names() == ["start_server", *commands, "set_volume"]
        assert moc.state is expected
        if expected is not MocState.STOP:
            assert (moc.index, moc.seconds) == (1, 0)
            assert app._state.played_path == str(album)

    @pytest.mark.parametrize("state", ["pause", "play", "stop", "use_saved"])
    def test_startup_state_has_no_effect_when_selecting_from_the_library(
        self, mocker, tmp_path, album, state
    ):
        moc = FakeMoc()
        moc.play(album)
        moc.calls.clear()
        app, moc = self.start(
            mocker, tmp_path, album, "open_library", state, MocState.PLAY, moc=moc
        )
        assert moc.names() == ["start_server", "stop", "set_volume"]
        assert moc.state is MocState.STOP
        assert [menu.title for menu in app._state.menus] == ["Menu", "Library"]

    def test_startup_state_setting_is_saved(self, tmp_path):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration("none", "none"), path)
        assert app._state.settings.startup_state is StartupState.USE_SAVED
        events = (
            ButtonEvent(Button.A, Press.LONG),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
            ButtonEvent(Button.Y),
            ButtonEvent(Button.B),
            ButtonEvent(Button.X),
            ButtonEvent(Button.B),
        )
        for event in events:
            app._controller.handle(event)
        assert app._state.settings.startup_state is StartupState.STOP
        assert load_configuration(path).startup.state == "stop"

    def test_playback_that_no_longer_exists_is_blanked(self, mocker, tmp_path):
        moc = FakeMoc()
        mocker.patch("mocassino.app.SubprocessMocClient", return_value=moc)
        state_file_path = tmp_path / "state.yaml"
        StateFile(state_file_path).save(
            SavedState(
                directory_path=str(tmp_path / "gone"),
                file_path=str(tmp_path / "gone" / "01.flac"),
                seek=95,
                state=MocState.PLAY,
                volume=70,
            )
        )
        app = build_app(self.configuration("none", "none"), state_file_path=state_file_path)
        app.start()
        assert moc.names() == ["start_server", "stop", "set_volume"]
        assert moc.volume == 70
        assert StateFile(state_file_path).load() == SavedState(volume=70)

    def test_reset_settings(self, mocker, tmp_path):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        moc.status.return_value = PLAYING
        path = tmp_path / "custom.yaml"
        path.write_text(
            "display:\n"
            "  brightness: 0.4\n"
            "  show_side_icons: false\n"
            "library:\n"
            "  directory_path: /srv/music\n"
            "playback:\n"
            "  volume_step: 10\n",
            encoding="utf-8",
        )
        configuration = load_configuration(
            path,
            {"buttons": {"origin": "none"}, "display": {"target": "none"}},
        )
        app = build_app(configuration, path)
        settings = app._state.settings
        assert (settings.display_brightness, settings.show_side_icons) == (40, False)
        for event in RESET_SETTINGS:
            app.events.put(event)
        app.step()
        assert app._state.settings is settings
        assert settings == Settings()
        assert app._display.brightness == 1.0
        assert [menu.title for menu in app._state.menus] == ["Menu", "System"]
        assert load_configuration(path) == Configuration()

    @pytest.mark.parametrize(
        ("origin", "target"),
        [("simulator", "none"), ("none", "simulator"), ("simulator", "simulator")],
    )
    def test_reset_settings_keeps_the_simulator(self, tmp_path, origin, target):
        path = tmp_path / "custom.yaml"
        app = build_app(self.configuration(origin, target), path)
        for event in RESET_SETTINGS:
            app._controller.handle(event)
        written = load_configuration(path)
        assert written.buttons.origin == ("simulator" if origin == "simulator" else "pirateaudio")
        assert written.display.target == ("simulator" if target == "simulator" else "pirateaudio")
        assert written.library == Configuration().library

    def test_reset_settings_to_the_default_file(self, tmp_path):
        app = build_app(self.configuration("none", "none"))
        for event in RESET_SETTINGS:
            app._controller.handle(event)
        path = tmp_path / ".config" / "mocassino" / "configuration.yaml"
        assert load_configuration(path) == Configuration()

    def test_reset_settings_cannot_be_written(self, tmp_path, caplog):
        blocker = tmp_path / "blocker"
        blocker.touch()
        app = build_app(self.configuration("none", "none"), blocker / "configuration.yaml")
        app._state.settings.show_volume_bar = False
        with caplog.at_level(logging.ERROR):
            for event in RESET_SETTINGS:
                app._controller.handle(event)
        assert "Cannot reset the settings: Cannot write configuration file" in caplog.text
        assert app._state.settings == Settings()

    def test_shutdown_turns_the_display_off(self, mocker):
        system = mocker.patch("mocassino.app.System", autospec=True).return_value
        system.hostname.return_value = "pirate"
        system.ip_address.return_value = None
        app = build_app(self.configuration("none", "none"))
        display = app._display
        system.shutdown.side_effect = lambda: mocker.sentinel.done if not display.is_on else 1 / 0
        for event in SHUT_DOWN:
            app._controller.handle(event)
        system.shutdown.assert_called_once_with()
        assert display.is_on is False
        assert app._state.shutting_down is True

    def test_shutdown_that_fails_turns_the_display_on_again(self, mocker):
        system = mocker.patch("mocassino.app.System", autospec=True).return_value
        system.hostname.return_value = "pirate"
        system.ip_address.return_value = None
        system.shutdown.side_effect = SystemShutdownError("denied")
        app = build_app(self.configuration("none", "none"))
        for event in SHUT_DOWN:
            app._controller.handle(event)
        system.shutdown.assert_called_once_with()
        assert app._display.is_on is True
        assert app._state.shutting_down is False
        app._moc = mocker.create_autospec(SubprocessMocClient, instance=True)
        app._moc.status.return_value = PLAYING
        app.step()
        assert app._state_frozen is False

    @pytest.mark.parametrize(
        ("origin", "target", "dry_run"),
        [
            ("none", "none", False),
            ("simulator", "none", True),
            ("none", "simulator", True),
            ("simulator", "simulator", True),
        ],
    )
    def test_shutdown_is_a_dry_run_with_the_simulator(self, mocker, origin, target, dry_run):
        system_class = mocker.patch("mocassino.app.System", autospec=True)
        build_app(self.configuration(origin, target))
        system_class.assert_called_once_with(
            dry_run=dry_run,
            reboot_command=("sudo", "reboot"),
            shutdown_command=("sudo", "shutdown", "-h", "now"),
        )

    def test_reboot_with_the_simulator_runs_no_command(self, mocker, caplog):
        run = mocker.patch("mocassino.model.system.subprocess.run")
        app = build_app(self.configuration("simulator", "simulator"))
        with caplog.at_level(logging.WARNING):
            for event in REBOOT:
                app._controller.handle(event)
        run.assert_not_called()
        assert "Not rebooting the host (dry run)" in caplog.text
        assert app._state.shutting_down is True

    def test_reboot_without_the_simulator_runs_the_command(self, mocker):
        run = mocker.patch(
            "mocassino.model.system.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        )
        configuration = load_configuration(
            overrides={
                "buttons": {"origin": "none"},
                "display": {"target": "none"},
                "system": {"reboot_command": "systemctl reboot"},
            }
        )
        app = build_app(configuration)
        for event in REBOOT:
            app._controller.handle(event)
        assert run.call_args.args[0] == ["systemctl", "reboot"]
        assert app._display.is_on is False

    def test_shutdown_with_the_simulator_runs_no_command(self, mocker):
        run = mocker.patch("mocassino.model.system.subprocess.run")
        app = build_app(self.configuration("simulator", "simulator"))
        for event in SHUT_DOWN:
            app._controller.handle(event)
        run.assert_not_called()
        assert app._state.shutting_down is True

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
