"""Tests for the settings that can be changed while the service runs.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.constants import MocStateOnExit, StartupPlaylist, StartupState, StartupVolume
from mocassino.model.settings import Settings


class TestSettings:
    """Tests for the Settings class"""

    def test_reset_all_colors(self):
        settings = Settings(
            display_brightness=40,
            display_colors_accented="red",
            display_colors_background="#123456",
            display_colors_muted="navy",
            display_colors_normal="black",
            display_colors_track="gold",
        )
        settings.reset_all_colors()
        assert settings == Settings(display_brightness=40)

    def test_update(self):
        settings = Settings()
        other = Settings(
            display_brightness=40,
            display_orientation=180,
            playback_seek_step=30,
            playback_volume_default=20,
            playback_volume_step=2,
            show_progress_bar=False,
            show_side_icons=False,
            show_timers=False,
            show_volume_bar=False,
            startup_playlist=StartupPlaylist.OPEN_LIBRARY,
            startup_state=StartupState.PLAY,
            startup_volume=StartupVolume.USE_DEFAULT,
            system_moc_state_on_exit=MocStateOnExit.QUIT,
        )
        same = settings
        settings.update(other)
        assert settings is same
        assert settings == other
        assert settings is not other

    def test_update_to_the_defaults(self):
        settings = Settings(display_brightness=40, show_side_icons=False)
        settings.update(Settings())
        assert settings == Settings()
