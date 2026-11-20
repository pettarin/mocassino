"""The colors the renderer draws with.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from collections.abc import Mapping
from dataclasses import dataclass

from mocassino.defaults import DEFAULT_COLOR_SPECS
from mocassino.model.colors import Color, parse_color


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


def parse_colors(specs: Mapping[str, str]) -> Colors:
    """Return the colors of the given names or HTML codes, one per role.

    :raises ValueError: if a color is not valid
    """
    return Colors(**{role: parse_color(spec) for role, spec in specs.items()})


# Defined last, as it needs the function above
DEFAULT_COLORS: Colors = parse_colors(DEFAULT_COLOR_SPECS)
