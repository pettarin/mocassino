"""The settings that can be changed while the service runs, from the settings menu.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from dataclasses import dataclass
from enum import StrEnum


class StartupPlaylist(StrEnum):
    """What the service does about the playlist when it starts.

    Defined before the settings, as they refer to it.
    """

    SELECT_FROM_LIBRARY = "select_from_library"
    USE_MOCP_STATE = "use_mocp_state"
    USE_SAVED = "use_saved"


@dataclass
class Settings:
    """The settings that can be changed while the service runs.

    Their initial values come from the configuration; the changes are not saved to it.
    """

    show_side_icons: bool = True
    startup_playlist: StartupPlaylist = StartupPlaylist.USE_SAVED
    use_saved_volume: bool = True
