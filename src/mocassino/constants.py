"""The constants of the service: the choices of the settings, and the limits of their values.

The configuration stores the choices as plain strings, the values of these enums
(e.g., "simulator" for ButtonsOrigin.SIMULATOR), as YAML cannot represent the enums.

This module imports nothing from the package, so that any module can import it.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from enum import StrEnum

# After how many seconds without a button press the display can be turned off; 0 for never
DISPLAY_TIMEOUT_CHOICES: tuple[int, ...] = (0, 5, 10, 15, 20, 30, 60, 120, 300)
# By how many degrees, clockwise, the display can be rotated
ORIENTATIONS: tuple[int, ...] = (0, 90, 180, 270)
# How long, in seconds, the main loop can wait for a button event, at most, before each refresh
REFRESH_DELAY_CHOICES: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 5.0)
# The volume levels of MOC
VOLUME_MAX: int = 100
VOLUME_MIN: int = 0


class Action(StrEnum):
    """What a button event can ask for."""

    MENU_BACK = "menu_back"
    MENU_DOWN = "menu_down"
    MENU_SELECT = "menu_select"
    MENU_UP = "menu_up"
    NEXT = "next"
    OPEN_MENU = "open_menu"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    SEEK_BACKWARD = "seek_backward"
    SEEK_FORWARD = "seek_forward"
    VOLUME_DOWN = "volume_down"
    VOLUME_UP = "volume_up"


class Button(StrEnum):
    """The four buttons of the Pirate Audio hat.

    A is top-left, B is bottom-left, X is top-right, and Y is bottom-right.
    """

    A = "A"
    B = "B"
    X = "X"
    Y = "Y"


class ButtonPress(StrEnum):
    """The kinds of press of a button.

    A button released early gives one short press.
    A button held gives one long press, as soon as it has been held long enough,
    and a hold press at the same time and then repeatedly, until it is released.
    """

    HOLD = "hold"
    LONG = "long"
    SHORT = "short"


class ButtonsOrigin(StrEnum):
    """Where the button events come from.

    PIRATEAUDIO is a synonym of GPIO, the buttons of the Pirate Audio hat.
    """

    GPIO = "gpio"
    NONE = "none"
    PIRATEAUDIO = "pirateaudio"
    SIMULATOR = "simulator"


class DisplayTarget(StrEnum):
    """Where the screen is drawn.

    PIRATEAUDIO is a synonym of ST7789, the display of the Pirate Audio hat.
    """

    NONE = "none"
    PIRATEAUDIO = "pirateaudio"
    SIMULATOR = "simulator"
    ST7789 = "st7789"


class Mode(StrEnum):
    """The mode of the application."""

    MENU = "menu"
    PLAYBACK = "playback"


class MocStateOnExit(StrEnum):
    """What the service does to MOC when it exits."""

    DO_NOTHING = "do_nothing"
    PAUSE = "pause"
    QUIT = "quit"
    STOP = "stop"


class RightTimerValue(StrEnum):
    """What the timer on the right shows in playback mode.

    END_TIME is the time at which the track ends, that is, its length;
    REMAINING_TIME is the time left until then.
    """

    END_TIME = "end_time"
    REMAINING_TIME = "remaining_time"


class RunMode(StrEnum):
    """Whether the service runs in background, detached from the terminal, or in foreground."""

    BACKGROUND = "background"
    FOREGROUND = "foreground"


class StartupPlaylist(StrEnum):
    """What the service does about the playlist when it starts."""

    OPEN_LIBRARY = "open_library"
    USE_MOC_STATE = "use_moc_state"
    USE_SAVED = "use_saved"


class StartupState(StrEnum):
    """What playback state the service sets when it starts."""

    PAUSE = "pause"
    PLAY = "play"
    STOP = "stop"
    USE_SAVED = "use_saved"


class StartupVolume(StrEnum):
    """What volume the service sets when it starts."""

    USE_DEFAULT = "use_default"
    USE_SAVED = "use_saved"
