"""The default values of the configuration, and of the files the service reads and writes.

Each name follows the path of its setting in the configuration file
(e.g., DEFAULT_BUTTONS_LONG_PRESS_TIME for "buttons.long_press_time").
The values set to members of an enum (e.g., "startup.playlist") are given as plain strings,
the values of the members, as the configuration stores them.

This module imports only the constants module, so that any other module can import it.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from pathlib import Path

from mocassino.constants import (
    Action,
    Button,
    ButtonPress,
    ButtonsOrigin,
    DisplayTarget,
    MocStateOnExit,
    Mode,
    RightTimerValue,
    RunMode,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)

DEFAULT_BUTTONS_LONG_PRESS_TIME: float = 0.6
DEFAULT_BUTTONS_ORIGIN: str = ButtonsOrigin.PIRATEAUDIO.value
DEFAULT_BUTTONS_REPEAT_HOLD_TIME: float = 0.3
# The button map in plain form (see the actions module of the controller):
# the action of each button, by mode, with a suffix for the long and hold presses
DEFAULT_BUTTON_MAP: dict[str, dict[str, str]] = {
    Mode.MENU.value: {
        Button.A.value: Action.MENU_BACK.value,
        Button.B.value: Action.MENU_SELECT.value,
        Button.X.value: Action.MENU_UP.value,
        f"{Button.X}_{ButtonPress.LONG}": Action.MENU_SELECT.value,
        Button.Y.value: Action.MENU_DOWN.value,
        f"{Button.Y}_{ButtonPress.LONG}": Action.MENU_SELECT.value,
    },
    Mode.PLAYBACK.value: {
        Button.A.value: Action.PLAY_PAUSE.value,
        f"{Button.A}_{ButtonPress.LONG}": Action.OPEN_MENU.value,
        Button.B.value: Action.NEXT.value,
        f"{Button.B}_{ButtonPress.LONG}": Action.PREVIOUS.value,
        Button.X.value: Action.VOLUME_UP.value,
        f"{Button.X}_{ButtonPress.HOLD}": Action.SEEK_FORWARD.value,
        Button.Y.value: Action.VOLUME_DOWN.value,
        f"{Button.Y}_{ButtonPress.HOLD}": Action.SEEK_BACKWARD.value,
    },
}
# The default color of each role, as a name or an HTML code,
# in the order of COLOR_ROLES (see the colors module of the model)
DEFAULT_COLOR_SPECS: dict[str, str] = {
    "accented": "limegreen",
    "background": "black",
    "muted": "silver",
    "normal": "white",
    "track": "dimgray",
}
DEFAULT_CONFIGURATION_FILE_PATH: Path = Path("~/.config/mocassino/configuration.yaml")
DEFAULT_DISPLAY_BRIGHTNESS: float = 1.0
# None for the font bundled with mocassino (Roboto Regular)
DEFAULT_DISPLAY_FONT_FILE_PATH: Path | None = None
DEFAULT_DISPLAY_ORIENTATION: int = 0
DEFAULT_DISPLAY_TARGET: str = DisplayTarget.PIRATEAUDIO.value
DEFAULT_DISPLAY_TIMEOUT: int = 60
DEFAULT_DISPLAY_UI_ELEMENTS_RIGHT_TIMER_VALUE: str = RightTimerValue.END_TIME.value
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_TIMERS: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR: bool = True
# The home directory of the user running the service, expanded when the configuration is made
DEFAULT_LIBRARY_DIRECTORY_PATH: Path = Path("~")
DEFAULT_PLAYBACK_SEEK_STEP: int = 10
DEFAULT_PLAYBACK_VOLUME_DEFAULT: int = 50
DEFAULT_PLAYBACK_VOLUME_STEP: int = 5
DEFAULT_RUN_MOC_STATE_ON_EXIT: str = MocStateOnExit.DO_NOTHING.value
DEFAULT_RUN_MODE: str = RunMode.BACKGROUND.value
# How long, in seconds, the main loop waits for a button event, at most, before each refresh
DEFAULT_RUN_REFRESH_DELAY: float = 0.5
DEFAULT_RUN_SAVE_STATE_ON_EXIT: bool = True
DEFAULT_RUN_SAVE_STATE_ON_REFRESH: bool = False
DEFAULT_RUN_SAVE_STATE_ON_STARTUP: bool = True
DEFAULT_RUN_SAVE_STATE_ON_STATE_CHANGE: bool = True
DEFAULT_RUN_SAVE_STATE_ON_TRACK_CHANGE: bool = True
DEFAULT_RUN_SAVE_STATE_ON_VOLUME_CHANGE: bool = True
DEFAULT_STARTUP_PLAYLIST: str = StartupPlaylist.USE_SAVED.value
DEFAULT_STARTUP_STATE: str = StartupState.USE_SAVED.value
DEFAULT_STARTUP_VOLUME: str = StartupVolume.USE_SAVED.value
DEFAULT_STATE_FILE_PATH: Path = Path("~/.config/mocassino/state.yaml")
DEFAULT_SYSTEM_MOCP_FILE_PATH: str = "mocp"
DEFAULT_SYSTEM_REBOOT_COMMAND: tuple[str, ...] = ("sudo", "systemctl", "reboot")
DEFAULT_SYSTEM_SHUTDOWN_COMMAND: tuple[str, ...] = ("sudo", "shutdown", "-h", "now")
