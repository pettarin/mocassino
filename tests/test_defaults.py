"""Tests for the default values of the configuration.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.app import _build_settings
from mocassino.configuration import Configuration, _build
from mocassino.defaults import (
    DEFAULT_STARTUP_PLAYLIST,
    DEFAULT_STARTUP_STATE,
    DEFAULT_STARTUP_VOLUME,
    DEFAULT_SYSTEM_MOC_STATE_ON_EXIT,
)
from mocassino.model.settings import (
    MocStateOnExit,
    Settings,
    StartupPlaylist,
    StartupState,
    StartupVolume,
)


class TestDefaults:
    """Tests for the default values of the configuration"""

    def test_configuration_is_valid(self):
        assert _build({}) == Configuration()

    def test_enum_values(self):
        assert DEFAULT_STARTUP_PLAYLIST in list(StartupPlaylist)
        assert DEFAULT_STARTUP_STATE in list(StartupState)
        assert DEFAULT_STARTUP_VOLUME in list(StartupVolume)
        assert DEFAULT_SYSTEM_MOC_STATE_ON_EXIT in list(MocStateOnExit)

    def test_settings_match_configuration(self):
        assert _build_settings(Configuration()) == Settings()
