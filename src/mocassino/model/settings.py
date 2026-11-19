"""The settings that can be changed while the service runs, from the settings menu.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from dataclasses import dataclass
from enum import StrEnum

# By how many degrees, clockwise, the display can be rotated
ORIENTATIONS: tuple[int, ...] = (0, 90, 180, 270)


class StartupPlaylist(StrEnum):
    """What the service does about the playlist when it starts.

    Defined before the settings, as they refer to it.
    """

    OPEN_LIBRARY = "open_library"
    USE_MOCP_STATE = "use_mocp_state"
    USE_SAVED = "use_saved"


class StartupState(StrEnum):
    """What playback state the service sets when it starts.

    Defined before the settings, as they refer to it.
    """

    PAUSE = "pause"
    PLAY = "play"
    STOP = "stop"
    USE_SAVED = "use_saved"


class StartupVolume(StrEnum):
    """What volume the service sets when it starts.

    Defined before the settings, as they refer to it.
    """

    USE_DEFAULT = "use_default"
    USE_SAVED = "use_saved"


@dataclass
class Settings:
    """The settings that can be changed while the service runs.

    Their initial values come from the configuration; the changes are not saved to it.
    """

    display_orientation: int = 0
    playback_seek_step: int = 10
    playback_volume_default: int = 50
    playback_volume_step: int = 5
    show_progress_bar: bool = True
    show_side_icons: bool = True
    show_volume_bar: bool = True
    startup_playlist: StartupPlaylist = StartupPlaylist.USE_SAVED
    startup_state: StartupState = StartupState.USE_SAVED
    startup_volume: StartupVolume = StartupVolume.USE_SAVED
