"""Tests for the application.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from dataclasses import replace

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
from mocassino.model.state_file import SavedState, StateFile
from mocassino.simulator.tk import TkSimulator
from mocassino.view.display.null import NullDisplay
from mocassino.view.display.st7789 import St7789Display
from mocassino.view.renderer import Renderer
from tests.model.fake_moc import FakeMoc

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


@pytest.fixture
def state_file(mocker):
    state_file = mocker.create_autospec(StateFile, instance=True)
    state_file.load.return_value = SavedState()
    return state_file


@pytest.fixture
def saving_app(mocker, tmp_path, state, moc, display, button_source, state_file):
    """An application with a state file."""
    host = mocker.create_autospec(Host, instance=True)
    controller = Controller(
        state, moc, Library(tmp_path), host, DEFAULT_BUTTON_MAP, seek_step=10, volume_step=5
    )
    return App(
        state, controller, moc, Renderer(), display, button_source, TICK, state_file=state_file
    )


class TestApp:
    """Tests for the App class"""

    def test_state_is_saved(self, saving_app, state_file, moc):
        app = saving_app
        playing = SavedState(file_path="/music/a.flac", state=MocState.PLAY, volume=40)
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
            SavedState(file_path="/music/b.flac", seek=7, state=MocState.PAUSE, volume=45)
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
            SavedState(file_path="/music/b.flac", seek=60, state=MocState.PAUSE, volume=45)
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
        order.attach_mock(resume, "resume")
        order.attach_mock(moc.set_volume, "set_volume")
        saving_app.start()
        resume.assert_called_once_with(moc, saved)
        assert [call[0] for call in order.mock_calls] == ["resume", "set_volume"]
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
        assert "Cannot resume the saved playback: broken" in caplog.text
        moc.set_volume.assert_called_once_with(40)
        state_file.save.assert_called_once_with(SavedState(volume=40))

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
        app = build_app(
            self.configuration("none", "none", fallback_initial_volume=30, volume_step=10)
        )
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
        path.write_text("playback:\n  fallback_initial_volume: 30\n", encoding="utf-8")
        configuration = load_configuration(
            path,
            {"buttons": {"origin": "none"}, "display": {"target": "none"}},
        )
        app = build_app(configuration, path)
        for event in TOGGLE_SIDE_ICONS:
            app._controller.handle(event)
        assert app._state.settings.show_side_icons is False
        assert path.read_text(encoding="utf-8") == (
            "playback:\n  fallback_initial_volume: 30\ndisplay:\n  show_side_icons: false\n"
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
        assert app._state.current_menu.selected.checked is False

    def test_volume_from_the_configuration(self, tmp_path):
        state_file_path = tmp_path / "state.yaml"
        app = build_app(
            self.configuration("none", "none", fallback_initial_volume=30),
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
        app = build_app(self.configuration("none", "none", fallback_initial_volume=30))
        assert app._state.volume == 85

    def test_volume_from_the_state_file(self, mocker, tmp_path):
        moc = mocker.patch("mocassino.app.SubprocessMocClient", autospec=True).return_value
        moc.status.return_value = PLAYING
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text("playback:\n  volume: 85\n", encoding="utf-8")
        app = build_app(
            self.configuration("none", "none", fallback_initial_volume=30, volume_step=5),
            state_file_path=state_file_path,
        )
        assert app._state.volume == 85
        app.start()
        moc.set_volume.assert_called_once_with(85)
        app.events.put(ButtonEvent(Button.Y))
        app.step()
        moc.set_volume.assert_called_with(80)
        assert StateFile(state_file_path).load() == SavedState(
            file_path=PLAYING.file_path,
            state=MocState.PLAY,
            volume=80,
        )

    def test_volume_from_the_state_file_not_valid(self, tmp_path):
        state_file_path = tmp_path / "state.yaml"
        state_file_path.write_text("playback:\n  volume: 850\n", encoding="utf-8")
        app = build_app(
            self.configuration("none", "none", fallback_initial_volume=30),
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
        configuration = self.configuration("none", "none", fallback_initial_volume=30)
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
        assert moc.names()[:2] == ["start_server", "set_volume"]
        assert moc.names()[-1] == "set_volume"
        assert app._state.played_path == str(album)
        assert StateFile(state_file_path).load() == saved

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
        assert moc.names() == ["start_server", "set_volume"]
        assert moc.volume == 70
        assert StateFile(state_file_path).load() == SavedState(volume=70)

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
