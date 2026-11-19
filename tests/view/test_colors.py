"""Tests for the colors of the renderer.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.view.colors import (
    DEFAULT_COLOR_SPECS,
    DEFAULT_COLORS,
    Colors,
    parse_color,
    parse_colors,
)


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

    def test_default_color_specs(self):
        assert DEFAULT_COLOR_SPECS == {
            "accented": "limegreen",
            "background": "black",
            "muted": "silver",
            "normal": "white",
            "track": "dimgray",
        }


class TestParseColor:
    """Tests for the parse_color function"""

    @pytest.mark.parametrize(
        ("spec", "color"),
        [
            ("#00F", (0, 0, 255)),
            ("#0000FF", (0, 0, 255)),
            ("#0000ff", (0, 0, 255)),
            ("#FFB000", (255, 176, 0)),
            ("orange", (255, 165, 0)),
            ("darkgray", (169, 169, 169)),
            ("DarkGray", (169, 169, 169)),
            (" white ", (255, 255, 255)),
        ],
    )
    def test_valid(self, spec, color):
        assert parse_color(spec) == color

    @pytest.mark.parametrize("spec", ["blurple", "", "#12345", "#zzz", "00F"])
    def test_not_valid(self, spec):
        with pytest.raises(ValueError):
            parse_color(spec)

    @pytest.mark.parametrize("spec", [5, None, True, ["white"]])
    def test_not_a_string(self, spec):
        with pytest.raises(ValueError, match="expected a color name or an HTML code"):
            parse_color(spec)


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
