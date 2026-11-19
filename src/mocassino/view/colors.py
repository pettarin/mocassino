"""The colors the renderer draws with, and how they are read from their names or codes.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from dataclasses import dataclass

from colorzero import Color as ColorZero

type Color = tuple[int, int, int]

# The default color of each role, as a name or an HTML code
DEFAULT_COLOR_SPECS: dict[str, str] = {
    "accented": "limegreen",
    "background": "black",
    "muted": "silver",
    "normal": "white",
    "track": "dimgray",
}


@dataclass(frozen=True)
class Colors:
    """The colors the renderer draws with, one per role.

    - accented: what is highlighted (e.g., the progress, the selected menu item)
    - background: the background of the frame
    - muted: the secondary text and icons
    - normal: the main text
    - track: the background of the bars, and of the title of the menus
    """

    accented: Color
    background: Color
    muted: Color
    normal: Color
    track: Color


def parse_color(spec: str) -> Color:
    """Return the RGB color of an HTML code (e.g., "#00F" or "#0000FF") or of a CSS name.

    The names are not case-sensitive (e.g., "DarkGray" is "darkgray").

    :raises ValueError: if the color is neither a valid HTML code nor a known name
    """
    if not isinstance(spec, str):
        raise ValueError(f"expected a color name or an HTML code, not {spec!r}")
    text = spec.strip()
    if not text.startswith("#"):
        text = text.lower()
    red, green, blue = ColorZero(text).rgb_bytes
    return (red, green, blue)


def parse_colors(specs: dict[str, str]) -> Colors:
    """Return the colors of the given names or HTML codes, one per role.

    :raises ValueError: if a color is not valid
    """
    return Colors(**{role: parse_color(spec) for role, spec in specs.items()})


# Defined last, as it needs the functions above
DEFAULT_COLORS: Colors = parse_colors(DEFAULT_COLOR_SPECS)
