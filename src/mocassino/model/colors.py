"""The colors of the display: their names, their defaults, and how they are read.

A color is either an HTML code (e.g., "#00F" or "#0000FF") or a CSS color name
(e.g., "orange"), as accepted by colorzero.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from functools import cache

from colorzero import Color as ColorZero
from colorzero.tables import NAMED_COLORS

type Color = tuple[int, int, int]

# The color keywords of CSS3 (https://www.w3.org/TR/css-color-3/#svg-color),
# in alphabetical order, with the US English spelling of gray only
COLOR_NAMES: tuple[str, ...] = tuple(sorted(name for name in NAMED_COLORS if "grey" not in name))
# The roles of the colors: see the Colors class of the view
COLOR_ROLES: tuple[str, ...] = ("accented", "background", "muted", "normal", "track")
# The default color of each role, as a name or an HTML code
DEFAULT_COLOR_SPECS: dict[str, str] = {
    "accented": "limegreen",
    "background": "black",
    "muted": "silver",
    "normal": "white",
    "track": "dimgray",
}


@cache
def _parse_color(spec: str) -> Color:
    """Return the RGB color of a string; see parse_color.

    :raises ValueError: if the color is neither a valid HTML code nor a known name
    """
    text = spec.strip()
    if not text.startswith("#"):
        text = text.lower()
    red, green, blue = ColorZero(text).rgb_bytes
    return (red, green, blue)


def color_name(spec: str) -> str | None:
    """Return the name, among COLOR_NAMES, of the given color, or None if it has none.

    A name is returned as it is (e.g., "cyan"); a name spelled with grey,
    and an HTML code, are matched by their color, to the first name in alphabetical order
    (e.g., "darkgrey" to "darkgray", and "#00FFFF" to "aqua", not to "cyan").

    :raises ValueError: if the color is not valid
    """
    rgb = parse_color(spec)
    name = spec.strip().lower()
    if name in COLOR_NAMES:
        return name
    for candidate in COLOR_NAMES:
        if parse_color(candidate) == rgb:
            return candidate
    return None


def parse_color(spec: str) -> Color:
    """Return the RGB color of an HTML code (e.g., "#00F" or "#0000FF") or of a CSS name.

    The names are not case-sensitive (e.g., "DarkGray" is "darkgray").

    :raises ValueError: if the color is neither a valid HTML code nor a known name
    """
    if not isinstance(spec, str):
        raise ValueError(f"expected a color name or an HTML code, not {spec!r}")
    return _parse_color(spec)
