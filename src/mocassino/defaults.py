"""The default values of the configuration, and of the files the service reads and writes.

Each name follows the path of its setting in the configuration file
(e.g., DEFAULT_BUTTONS_LONG_PRESS_TIME for "buttons.long_press_time").
The values set to members of an enum (e.g., "startup.playlist") are given as plain strings.

This module imports nothing from the package, so that any module can import it.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from pathlib import Path

DEFAULT_BUTTONS_LONG_PRESS_TIME: float = 0.6
DEFAULT_BUTTONS_ORIGIN: str = "pirateaudio"
DEFAULT_BUTTONS_REPEAT_HOLD_TIME: float = 0.3
# The button map in plain form: see the actions module of the controller
DEFAULT_BUTTON_MAP: dict[str, dict[str, str]] = {
    "menu": {
        "A": "menu_back",
        "B": "menu_select",
        "X": "menu_up",
        "X_long": "menu_select",
        "Y": "menu_down",
        "Y_long": "menu_select",
    },
    "playback": {
        "A": "play_pause",
        "A_long": "open_menu",
        "B": "next",
        "B_long": "previous",
        "X": "volume_up",
        "X_hold": "seek_forward",
        "Y": "volume_down",
        "Y_hold": "seek_backward",
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
# None for the font built in Pillow
DEFAULT_DISPLAY_FONT_FILE_PATH: Path | None = None
DEFAULT_DISPLAY_ORIENTATION: int = 0
DEFAULT_DISPLAY_TARGET: str = "pirateaudio"
DEFAULT_DISPLAY_TICK: float = 0.5
DEFAULT_DISPLAY_TIMEOUT: int = 60
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS: bool = True
DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR: bool = True
DEFAULT_LIBRARY_DIRECTORY_PATH: Path = Path("/music")
DEFAULT_PLAYBACK_SEEK_STEP: int = 10
DEFAULT_PLAYBACK_VOLUME_DEFAULT: int = 50
DEFAULT_PLAYBACK_VOLUME_STEP: int = 5
DEFAULT_RUN_MODE: str = "background"
DEFAULT_STARTUP_PLAYLIST: str = "use_saved"
DEFAULT_STARTUP_STATE: str = "use_saved"
DEFAULT_STARTUP_VOLUME: str = "use_saved"
DEFAULT_STATE_FILE_PATH: Path = Path("~/.config/mocassino/state.yaml")
DEFAULT_SYSTEM_MOCP_FILE_PATH: str = "mocp"
DEFAULT_SYSTEM_MOC_STATE_ON_EXIT: str = "do_nothing"
DEFAULT_SYSTEM_REBOOT_COMMAND: tuple[str, ...] = ("sudo", "reboot")
DEFAULT_SYSTEM_SHUTDOWN_COMMAND: tuple[str, ...] = ("sudo", "shutdown", "-h", "now")
