"""Tests for the colors of the display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.model.colors import (
    COLOR_NAMES,
    COLOR_ROLES,
    DEFAULT_COLOR_SPECS,
    color_name,
    parse_color,
)


class TestConstants:
    """Tests for the constants of the colors"""

    def test_color_names(self):
        assert len(COLOR_NAMES) == 140
        assert list(COLOR_NAMES) == sorted(COLOR_NAMES)
        assert COLOR_NAMES[0] == "aliceblue"
        assert COLOR_NAMES[-1] == "yellowgreen"
        assert not [name for name in COLOR_NAMES if "grey" in name]
        assert {"aqua", "cyan", "fuchsia", "magenta", "gray", "darkslategray"} <= set(COLOR_NAMES)

    def test_color_roles(self):
        assert COLOR_ROLES == ("accented", "background", "muted", "normal", "track")
        assert tuple(DEFAULT_COLOR_SPECS) == COLOR_ROLES

    def test_default_color_specs(self):
        assert DEFAULT_COLOR_SPECS == {
            "accented": "limegreen",
            "background": "black",
            "muted": "silver",
            "normal": "white",
            "track": "dimgray",
        }
        assert all(spec in COLOR_NAMES for spec in DEFAULT_COLOR_SPECS.values())


class TestColorName:
    """Tests for the color_name function"""

    @pytest.mark.parametrize(
        ("spec", "name"),
        [
            ("cyan", "cyan"),
            ("aqua", "aqua"),
            ("Magenta", "magenta"),
            (" white ", "white"),
            ("darkgrey", "darkgray"),
            ("grey", "gray"),
            ("#00FFFF", "aqua"),
            ("#f0f", "fuchsia"),
            ("#696969", "dimgray"),
            ("#000", "black"),
            ("#123456", None),
            ("#FFB000", None),
        ],
    )
    def test_color_name(self, spec, name):
        assert color_name(spec) == name

    def test_not_valid(self):
        with pytest.raises(ValueError):
            color_name("blurple")


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
            ("darkgrey", (169, 169, 169)),
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
