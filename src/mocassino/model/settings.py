"""The settings that can be changed while the service runs, from the settings menu.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum

from mocassino.model.colors import COLOR_ROLES, DEFAULT_COLOR_SPECS

# By how many degrees, clockwise, the display can be rotated
ORIENTATIONS: tuple[int, ...] = (0, 90, 180, 270)


class MocStateOnExit(StrEnum):
    """What the service does to MOC when it exits.

    Defined before the settings, as they refer to it.
    """

    DO_NOTHING = "do_nothing"
    PAUSE = "pause"
    QUIT = "quit"
    STOP = "stop"


class StartupPlaylist(StrEnum):
    """What the service does about the playlist when it starts.

    Defined before the settings, as they refer to it.
    """

    OPEN_LIBRARY = "open_library"
    USE_MOC_STATE = "use_moc_state"
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

    display_brightness: int = 100
    display_colors_accented: str = DEFAULT_COLOR_SPECS["accented"]
    display_colors_background: str = DEFAULT_COLOR_SPECS["background"]
    display_colors_muted: str = DEFAULT_COLOR_SPECS["muted"]
    display_colors_normal: str = DEFAULT_COLOR_SPECS["normal"]
    display_colors_track: str = DEFAULT_COLOR_SPECS["track"]
    display_orientation: int = 0
    playback_seek_step: int = 10
    playback_volume_default: int = 50
    playback_volume_step: int = 5
    show_playlist_bar: bool = True
    show_progress_bar: bool = True
    show_side_icons: bool = True
    show_volume_bar: bool = True
    startup_playlist: StartupPlaylist = StartupPlaylist.USE_SAVED
    startup_state: StartupState = StartupState.USE_SAVED
    startup_volume: StartupVolume = StartupVolume.USE_SAVED
    system_moc_state_on_exit: MocStateOnExit = MocStateOnExit.DO_NOTHING

    def color_specs(self) -> dict[str, str]:
        """Return the colors of the display, as names or HTML codes, by role."""
        return {role: getattr(self, f"display_colors_{role}") for role in COLOR_ROLES}

    def reset_all_colors(self) -> None:
        """Set the colors of the display to the default ones."""
        for role, spec in DEFAULT_COLOR_SPECS.items():
            setattr(self, f"display_colors_{role}", spec)

    def update(self, other: Settings) -> None:
        """Copy all the values of the other settings into these.

        The settings are changed in place, as the menus refer to them.
        """
        for item in fields(self):
            setattr(self, item.name, getattr(other, item.name))
