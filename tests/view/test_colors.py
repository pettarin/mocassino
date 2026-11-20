"""Tests for the colors of the renderer.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.defaults import DEFAULT_COLOR_SPECS
from mocassino.view.colors import DEFAULT_COLORS, Colors, parse_colors


class TestDefaultColors:
    """Tests for the default colors"""

    def test_default_colors(self):
        assert DEFAULT_COLORS == Colors(
            accented=(50, 205, 50),
            background=(0, 0, 0),
            muted=(192, 192, 192),
            normal=(255, 255, 255),
            track=(105, 105, 105),
        )


class TestParseColors:
    """Tests for the parse_colors function"""

    def test_parse_colors(self):
        colors = parse_colors(
            {
                "accented": "red",
                "background": "#FFF",
                "muted": "gray",
                "normal": "#000000",
                "track": "navy",
            }
        )
        assert colors == Colors(
            accented=(255, 0, 0),
            background=(255, 255, 255),
            muted=(128, 128, 128),
            normal=(0, 0, 0),
            track=(0, 0, 128),
        )

    def test_not_valid(self):
        specs = dict(DEFAULT_COLOR_SPECS, muted="blurple")
        with pytest.raises(ValueError):
            parse_colors(specs)
