"""The icons of the actions, drawn next to the buttons performing them.

Each icon is a mask of ICON_SIZE x ICON_SIZE pixels, drawn with a few shapes.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from collections.abc import Callable
from functools import cache

from PIL import Image, ImageDraw

from mocassino.controller.actions import Action

ICON_SIZE: int = 16


def _draw_next(draw: ImageDraw.ImageDraw) -> None:
    """Draw a triangle pointing right, followed by a bar."""
    draw.polygon([(1, 2), (10, 7), (10, 8), (1, 13)], fill=1)
    draw.rectangle((12, 2, 14, 13), fill=1)


def _draw_open_menu(draw: ImageDraw.ImageDraw) -> None:
    """Draw three horizontal bars."""
    for top in (3, 7, 11):
        draw.rectangle((1, top, 14, top + 1), fill=1)


def _draw_play_pause(draw: ImageDraw.ImageDraw) -> None:
    """Draw a triangle pointing right, followed by two bars."""
    draw.polygon([(0, 2), (6, 7), (6, 8), (0, 13)], fill=1)
    draw.rectangle((9, 2, 11, 13), fill=1)
    draw.rectangle((13, 2, 15, 13), fill=1)


def _draw_seek_forward(draw: ImageDraw.ImageDraw) -> None:
    """Draw two triangles pointing right."""
    draw.polygon([(0, 2), (7, 7), (7, 8), (0, 13)], fill=1)
    draw.polygon([(8, 2), (15, 7), (15, 8), (8, 13)], fill=1)


def _draw_speaker(draw: ImageDraw.ImageDraw) -> None:
    """Draw a speaker, on the left half of the icon."""
    draw.rectangle((0, 5, 3, 10), fill=1)
    draw.polygon([(3, 5), (7, 1), (7, 14), (3, 10)], fill=1)


def _draw_volume_down(draw: ImageDraw.ImageDraw) -> None:
    """Draw a speaker, followed by a minus sign."""
    _draw_speaker(draw)
    draw.rectangle((10, 7, 15, 8), fill=1)


def _draw_volume_up(draw: ImageDraw.ImageDraw) -> None:
    """Draw a speaker, followed by a plus sign."""
    _draw_speaker(draw)
    draw.rectangle((10, 7, 15, 8), fill=1)
    draw.rectangle((12, 5, 13, 10), fill=1)


def draw_icon(
    draw: ImageDraw.ImageDraw,
    action: Action,
    left: int,
    top: int,
    color: tuple[int, int, int],
) -> bool:
    """Draw the icon of the given action, with its top-left corner at the given position.

    :return: whether the action has an icon; if not, nothing is drawn
    """
    mask = icon_mask(action)
    if mask is None:
        return False
    draw.bitmap((left, top), mask, fill=color)
    return True


@cache
def icon_mask(action: Action) -> Image.Image | None:
    """Return the icon of the given action, or None if the action has no icon.

    The icons of the backward actions are those of the forward ones, mirrored.
    """
    drawers: dict[Action, Callable[[ImageDraw.ImageDraw], None]] = {
        Action.NEXT: _draw_next,
        Action.OPEN_MENU: _draw_open_menu,
        Action.PLAY_PAUSE: _draw_play_pause,
        Action.SEEK_FORWARD: _draw_seek_forward,
        Action.VOLUME_DOWN: _draw_volume_down,
        Action.VOLUME_UP: _draw_volume_up,
    }
    mirrored: dict[Action, Action] = {
        Action.PREVIOUS: Action.NEXT,
        Action.SEEK_BACKWARD: Action.SEEK_FORWARD,
    }
    source = mirrored.get(action, action)
    drawer = drawers.get(source)
    if drawer is None:
        return None
    mask = Image.new("1", (ICON_SIZE, ICON_SIZE), 0)
    drawer(ImageDraw.Draw(mask))
    if source is not action:
        return mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return mask
