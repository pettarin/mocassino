"""Tests for the icons.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import Image, ImageDraw

from mocassino.controller.actions import Action
from mocassino.model.moc import MocState
from mocassino.view.icons import (
    ICON_SIZE,
    draw_icon,
    draw_state_icon,
    icon_mask,
    state_icon_mask,
)

WITH_ICON = [
    Action.NEXT,
    Action.OPEN_MENU,
    Action.PLAY_PAUSE,
    Action.PREVIOUS,
    Action.SEEK_BACKWARD,
    Action.SEEK_FORWARD,
    Action.VOLUME_DOWN,
    Action.VOLUME_UP,
]
WITHOUT_ICON = [Action.MENU_BACK, Action.MENU_DOWN, Action.MENU_SELECT, Action.MENU_UP]


def mirrored(mask):
    """Return the mask, flipped left to right."""
    return mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


class TestDrawIcon:
    """Tests for the draw_icon function"""

    @pytest.mark.parametrize("action", WITH_ICON)
    def test_action_with_icon(self, action):
        image = Image.new("RGB", (3 * ICON_SIZE, 3 * ICON_SIZE))
        assert draw_icon(ImageDraw.Draw(image), action, ICON_SIZE, ICON_SIZE, (1, 2, 3))
        left, top, right, bottom = image.getbbox()
        assert ICON_SIZE <= left < right <= 2 * ICON_SIZE
        assert ICON_SIZE <= top < bottom <= 2 * ICON_SIZE
        assert {color for _, color in image.getcolors()} == {(0, 0, 0), (1, 2, 3)}

    @pytest.mark.parametrize("action", WITHOUT_ICON)
    def test_action_without_icon(self, action):
        image = Image.new("RGB", (3 * ICON_SIZE, 3 * ICON_SIZE))
        assert not draw_icon(ImageDraw.Draw(image), action, ICON_SIZE, ICON_SIZE, (1, 2, 3))
        assert image.getbbox() is None


class TestIconMask:
    """Tests for the icon_mask function"""

    def test_all_actions_are_covered(self):
        assert sorted(WITH_ICON + WITHOUT_ICON) == sorted(Action)

    @pytest.mark.parametrize("action", WITH_ICON)
    def test_action_with_icon(self, action):
        mask = icon_mask(action)
        assert mask.mode == "1"
        assert mask.size == (ICON_SIZE, ICON_SIZE)
        assert mask.getbbox() is not None

    @pytest.mark.parametrize("action", WITHOUT_ICON)
    def test_action_without_icon(self, action):
        assert icon_mask(action) is None

    def test_backward_icons_mirror_the_forward_ones(self):
        previous, following = icon_mask(Action.PREVIOUS), icon_mask(Action.NEXT)
        backward, forward = icon_mask(Action.SEEK_BACKWARD), icon_mask(Action.SEEK_FORWARD)
        assert previous.tobytes() == mirrored(following).tobytes()
        assert backward.tobytes() == mirrored(forward).tobytes()
        assert previous.tobytes() != following.tobytes()
        assert backward.tobytes() != forward.tobytes()

    def test_icons_are_all_different(self):
        assert len({icon_mask(action).tobytes() for action in WITH_ICON}) == len(WITH_ICON)

    def test_icons_are_vertically_symmetric(self):
        for action in WITH_ICON:
            mask = icon_mask(action)
            top, bottom = mask.getbbox()[1], mask.getbbox()[3]
            assert top == ICON_SIZE - bottom, action

    def test_volume_icons_differ_by_the_plus_sign(self):
        down, up = icon_mask(Action.VOLUME_DOWN), icon_mask(Action.VOLUME_UP)
        assert down.getpixel((12, 7)) and up.getpixel((12, 7))
        assert not down.getpixel((12, 5))
        assert up.getpixel((12, 5))


class TestStateIcon:
    """Tests for the state_icon_mask and draw_state_icon functions"""

    @pytest.mark.parametrize("state", list(MocState))
    def test_draw(self, state):
        image = Image.new("RGB", (3 * ICON_SIZE, 3 * ICON_SIZE))
        draw_state_icon(ImageDraw.Draw(image), state, ICON_SIZE, ICON_SIZE, (1, 2, 3))
        left, top, right, bottom = image.getbbox()
        assert ICON_SIZE <= left < right <= 2 * ICON_SIZE
        assert ICON_SIZE <= top < bottom <= 2 * ICON_SIZE
        assert {color for _, color in image.getcolors()} == {(0, 0, 0), (1, 2, 3)}

    @pytest.mark.parametrize("state", list(MocState))
    def test_mask(self, state):
        mask = state_icon_mask(state)
        assert mask.mode == "1"
        assert mask.size == (ICON_SIZE, ICON_SIZE)
        left, top, right, bottom = mask.getbbox()
        assert top == ICON_SIZE - bottom
        assert 2 <= top <= 3
        assert left == 3

    def test_masks_are_all_different(self):
        assert len({state_icon_mask(state).tobytes() for state in MocState}) == 3

    def test_pause_has_two_bars(self):
        mask = state_icon_mask(MocState.PAUSE)
        row = [bool(mask.getpixel((x, 7))) for x in range(ICON_SIZE)]
        bars = sum(1 for x in range(1, ICON_SIZE) if row[x] and not row[x - 1]) + row[0]
        assert bars == 2

    def test_play_points_right(self):
        mask = state_icon_mask(MocState.PLAY)
        assert mask.getpixel((3, 2)) and mask.getpixel((3, 13)) and mask.getpixel((13, 7))
        assert not mask.getpixel((13, 2)) and not mask.getpixel((13, 13))

    def test_stop_is_a_square(self):
        left, top, right, bottom = state_icon_mask(MocState.STOP).getbbox()
        assert right - left == bottom - top == 10
        assert state_icon_mask(MocState.STOP).crop((left, top, right, bottom)).getextrema()[0]
