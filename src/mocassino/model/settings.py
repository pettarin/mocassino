"""The settings that can be changed while the service runs, from the settings menu.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from mocassino.constants import (
    MocStateOnExit,
    RightTimerValue,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)
from mocassino.defaults import (
    DEFAULT_COLOR_SPECS,
    DEFAULT_DISPLAY_BRIGHTNESS,
    DEFAULT_DISPLAY_ORIENTATION,
    DEFAULT_DISPLAY_TIMEOUT,
    DEFAULT_DISPLAY_UI_ELEMENTS_RIGHT_TIMER_VALUE,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_TIMERS,
    DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR,
    DEFAULT_PLAYBACK_SEEK_STEP,
    DEFAULT_PLAYBACK_VOLUME_DEFAULT,
    DEFAULT_PLAYBACK_VOLUME_STEP,
    DEFAULT_STARTUP_PLAYLIST,
    DEFAULT_STARTUP_STATE,
    DEFAULT_STARTUP_VOLUME,
    DEFAULT_SYSTEM_MOC_STATE_ON_EXIT,
)
from mocassino.model.colors import COLOR_ROLES


@dataclass
class Settings:
    """The settings that can be changed while the service runs.

    Their initial values come from the configuration; the changes are not saved to it.
    """

    display_brightness: int = round(DEFAULT_DISPLAY_BRIGHTNESS * 100)
    display_colors_accented: str = DEFAULT_COLOR_SPECS["accented"]
    display_colors_background: str = DEFAULT_COLOR_SPECS["background"]
    display_colors_muted: str = DEFAULT_COLOR_SPECS["muted"]
    display_colors_normal: str = DEFAULT_COLOR_SPECS["normal"]
    display_colors_track: str = DEFAULT_COLOR_SPECS["track"]
    display_orientation: int = DEFAULT_DISPLAY_ORIENTATION
    display_timeout: int = DEFAULT_DISPLAY_TIMEOUT
    playback_seek_step: int = DEFAULT_PLAYBACK_SEEK_STEP
    playback_volume_default: int = DEFAULT_PLAYBACK_VOLUME_DEFAULT
    playback_volume_step: int = DEFAULT_PLAYBACK_VOLUME_STEP
    right_timer_value: RightTimerValue = RightTimerValue(
        DEFAULT_DISPLAY_UI_ELEMENTS_RIGHT_TIMER_VALUE
    )
    show_playlist_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PLAYLIST_BAR
    show_progress_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_PROGRESS_BAR
    show_side_icons: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_SIDE_ICONS
    show_timers: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_TIMERS
    show_volume_bar: bool = DEFAULT_DISPLAY_UI_ELEMENTS_SHOW_VOLUME_BAR
    startup_playlist: StartupPlaylist = StartupPlaylist(DEFAULT_STARTUP_PLAYLIST)
    startup_state: StartupState = StartupState(DEFAULT_STARTUP_STATE)
    startup_volume: StartupVolume = StartupVolume(DEFAULT_STARTUP_VOLUME)
    system_moc_state_on_exit: MocStateOnExit = MocStateOnExit(DEFAULT_SYSTEM_MOC_STATE_ON_EXIT)

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
