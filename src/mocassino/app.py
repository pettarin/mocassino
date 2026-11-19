"""The application: wires the model, the view, and the controller, and runs the main loop.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import threading
from dataclasses import astuple
from functools import partial
from pathlib import Path
from queue import Empty, Queue

from mocassino.configuration import (
    Configuration,
    ConfigurationError,
    update_configuration_file,
)
from mocassino.controller.buttons.base import ButtonSource
from mocassino.controller.buttons.gpio import GpioButtonSource
from mocassino.controller.buttons.null import NullButtonSource
from mocassino.controller.controller import Controller
from mocassino.controller.events import ButtonEvent
from mocassino.model.host import Host
from mocassino.model.library import Library
from mocassino.model.moc import (
    MocClient,
    MocError,
    MocServerNotRunningError,
    MocState,
    SubprocessMocClient,
)
from mocassino.model.resume import adopt_playback, playing_from, resume_playback
from mocassino.model.settings import Settings, StartupPlaylist
from mocassino.model.state import AppState
from mocassino.model.state_file import SavedState, StateFile
from mocassino.simulator.tk import TkSimulator
from mocassino.view.display.base import Display
from mocassino.view.display.null import NullDisplay
from mocassino.view.display.st7789 import St7789Display
from mocassino.view.renderer import Renderer

LOGGER: logging.Logger = logging.getLogger(__name__)


class App:
    """The application and its main loop.

    At each step, it handles the button events, asks MOC for its status,
    and draws the state on the display, if what is shown would change.

    The state is saved to the state file, if there is one, when the track, the volume,
    or a setting changes, and when the application is closed.
    When the application starts, the playback saved there is resumed, if possible.
    """

    def __init__(
        self,
        state: AppState,
        controller: Controller,
        moc: MocClient,
        renderer: Renderer,
        display: Display,
        button_source: ButtonSource,
        tick: float,
        simulator: TkSimulator | None = None,
        state_file: StateFile | None = None,
    ) -> None:
        """Initialize the application.

        :param tick: the maximum duration of a step of the main loop, in seconds
        :param simulator: the simulator used as display or button source, if any
        :param state_file: the file where the state is saved, if any
        """
        self._button_source = button_source
        self._controller = controller
        self._display = display
        self._events: Queue[ButtonEvent] = Queue()
        self._last_error: str | None = None
        self._last_frame: bytes | None = None
        self._moc = moc
        self._renderer = renderer
        self._simulator = simulator
        self._state = state
        self._state_file = state_file
        self._state_frozen = False
        self._stop = threading.Event()
        self._tick = tick
        # Last, as it needs the state
        self._saved_signature = self._signature()

    def _draw(self) -> None:
        """Draw the state on the display, unless the frame is the one already shown."""
        image = self._renderer.render(self._state)
        frame = image.tobytes()
        if frame != self._last_frame:
            self._display.show(image)
            self._last_frame = frame

    def _refresh(self) -> None:
        """Ask MOC for its status; if the MOC server is not running, start it.

        The errors are logged, not raised; an error that repeats is logged once.
        """
        try:
            try:
                self._state.status = self._moc.status()
                self._last_error = None
            except MocServerNotRunningError:
                LOGGER.warning("The MOC server is not running: starting it")
                self._moc.start_server()
        except MocError as exc:
            if str(exc) != self._last_error:
                LOGGER.error("Cannot get the MOC status: %s", exc)
                self._last_error = str(exc)

    def _save_state(self) -> None:
        """Save the state to the state file, if there is one.

        The directory saved is what MOC was given to play, if known and if the track
        being played is inside it; otherwise, the directory of that track.
        """
        if self._state_file is not None and not self._state_frozen:
            state, status = self._state, self._state.status
            playing = status.state is not MocState.STOP and status.file_path != ""
            self._state_file.save(
                SavedState(
                    directory_path=(
                        playing_from(state.played_path, status.file_path) if playing else None
                    ),
                    file_path=status.file_path if playing else None,
                    seek=status.current_seconds if playing else 0,
                    state=status.state if playing else MocState.STOP,
                    volume=state.volume,
                )
            )
        self._saved_signature = self._signature()

    def _signature(self) -> tuple[object, ...]:
        """Return what, when it changes, makes the state be saved.

        That is: the track, the volume, and the settings changed through the menus.
        """
        state = self._state
        return (state.status.file_path, state.volume, astuple(state.settings))

    def close(self) -> None:
        """Save the state, and release the buttons and the display."""
        self._save_state()
        self._button_source.close()
        self._display.close()

    @property
    def events(self) -> Queue[ButtonEvent]:
        """The queue of the button events to handle."""
        return self._events

    def run(self) -> None:
        """Run the main loop until the application is stopped, then release the hardware.

        :raises MocError: if the MOC server cannot be started or the volume cannot be set
        """
        try:
            self.start()
            while not self._stop.is_set():
                self.step()
        finally:
            self.close()

    @property
    def simulator(self) -> TkSimulator | None:
        """The simulator used as display or button source, if any; it has to be run too."""
        return self._simulator

    def start(self) -> None:
        """Start the MOC server, set up the playlist, and start listening to the buttons.

        What happens to the playlist depends on the startup playlist setting:
        MOC is stopped, and the playback saved in the state file is resumed (if it cannot be,
        nothing is played); or MOC is stopped, and the menu of the library is shown;
        or MOC is left as it is.
        The state file is then updated to say what is playing.
        The volume is set after the playlist is set up, as resuming needs it at zero.

        :raises MocError: if the MOC server cannot be started or the volume cannot be set
        """
        self._moc.start_server()
        saved = SavedState() if self._state_file is None else self._state_file.load()
        choice = self._state.settings.startup_playlist
        try:
            if choice is StartupPlaylist.USE_MOCP_STATE:
                self._state.played_path = adopt_playback(self._moc, saved)
            else:
                self._moc.stop()
                if choice is StartupPlaylist.USE_SAVED:
                    self._state.played_path = resume_playback(self._moc, saved)
                else:
                    self._controller.choose_folder()
        except MocError as exc:
            LOGGER.error("Cannot set up the playlist: %s", exc)
        self._moc.set_volume(self._state.volume)
        self._refresh()
        self._save_state()
        self._button_source.start(self._events)

    def step(self) -> None:
        """Perform one step of the main loop.

        Wait for a button event, for one tick at most; handle all the events in the queue;
        then update the state from MOC, save it if needed, and draw it.
        """
        try:
            self._controller.handle(self._events.get(timeout=self._tick))
            while True:
                self._controller.handle(self._events.get_nowait())
        except Empty:
            pass
        if self._state.shutting_down and not self._state_frozen:
            # Save what is playing before the shutdown stops it, and keep it as saved
            self._save_state()
            self._state_frozen = True
        self._refresh()
        if self._signature() != self._saved_signature:
            self._save_state()
        self._draw()

    def stop(self) -> None:
        """Ask the main loop to end; it does so within one tick."""
        self._stop.set()


def _build_button_source(
    configuration: Configuration,
    simulator: TkSimulator | None,
) -> ButtonSource:
    """Build the button source selected by the configuration."""
    origin = configuration.buttons.origin
    if origin in ("gpio", "pirateaudio"):
        return GpioButtonSource(
            long_press_time=configuration.buttons.long_press_time,
            repeat_hold_time=configuration.buttons.repeat_hold_time,
        )
    if origin == "simulator" and simulator is not None:
        return simulator
    return NullButtonSource()


def _build_display(configuration: Configuration, simulator: TkSimulator | None) -> Display:
    """Build the display selected by the configuration."""
    target = configuration.display.target
    if target == "simulator" and simulator is not None:
        return simulator
    if target in ("pirateaudio", "st7789"):
        return St7789Display()
    return NullDisplay()


def _save_settings(configuration_file_path: Path | None, settings: Settings) -> None:
    """Write the settings changed from the menus to the configuration file.

    An error is logged, not raised: the change still applies until the service stops.
    """
    updates: dict[str, dict[str, object]] = {
        "display": {"show_side_icons": settings.show_side_icons},
        "startup": {
            "playlist": settings.startup_playlist.value,
            "use_saved_volume": settings.use_saved_volume,
        },
    }
    try:
        path = update_configuration_file(configuration_file_path, updates)
    except ConfigurationError as exc:
        LOGGER.error("Cannot save the settings: %s", exc)
    else:
        LOGGER.info("Settings saved to '%s'", path)


def build_app(
    configuration: Configuration,
    configuration_file_path: Path | None = None,
    state_file_path: Path | None = None,
) -> App:
    """Build the application described by the configuration.

    If the buttons or the display are simulated, the application has a simulator,
    which has to be run in the main thread while the application runs in another one.

    The volume is the one saved in the state file, if any and if the configuration says
    to use it; otherwise, the fallback volume of the configuration.

    :param configuration_file_path: the YAML file where the settings changed from
                                    the settings menu are saved; if None, the default one
    :param state_file_path: the YAML file where the state is saved; if None, the default one
    :raises OSError: if the font or the display cannot be accessed
    """
    simulator: TkSimulator | None = None
    if "simulator" in (configuration.buttons.origin, configuration.display.target):
        simulator = TkSimulator(
            long_press_time=configuration.buttons.long_press_time,
            repeat_hold_time=configuration.buttons.repeat_hold_time,
        )
    host = Host(shutdown_command=configuration.system.shutdown_command)
    library = Library(directory_path=configuration.library.directory_path)
    moc = SubprocessMocClient(mocp_file_path=configuration.system.mocp_file_path)
    state_file = StateFile(state_file_path)
    volume = state_file.load().volume if configuration.startup.use_saved_volume else None
    if volume is None:
        volume = configuration.startup.fallback_volume
    state = AppState(
        settings=Settings(
            show_side_icons=configuration.display.show_side_icons,
            startup_playlist=StartupPlaylist(configuration.startup.playlist),
            use_saved_volume=configuration.startup.use_saved_volume,
        ),
        volume=volume,
    )
    controller = Controller(
        state,
        moc,
        library,
        host,
        button_map=configuration.buttons.button_map,
        seek_step=configuration.playback.seek_step,
        volume_step=configuration.playback.volume_step,
        save_settings=partial(_save_settings, configuration_file_path),
    )
    return App(
        state,
        controller,
        moc,
        renderer=Renderer(
            font_file_path=configuration.display.font_file_path,
            button_map=configuration.buttons.button_map,
        ),
        display=_build_display(configuration, simulator),
        button_source=_build_button_source(configuration, simulator),
        tick=configuration.display.tick,
        simulator=simulator,
        state_file=state_file,
    )
