"""Tests for the default values of the configuration.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.app import _build_settings
from mocassino.configuration import Configuration, _build
from mocassino.model.settings import Settings


class TestDefaults:
    """Tests for the default values of the configuration"""

    def test_configuration_is_valid(self):
        assert _build({}) == Configuration()

    def test_settings_match_configuration(self):
        assert _build_settings(Configuration()) == Settings()
