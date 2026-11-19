"""Tests for the button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.controller.events import Button, ButtonEvent, Press


class TestButtonEvent:
    """Tests for the ButtonEvent class"""

    @pytest.mark.parametrize(
        ("orientation", "expected"),
        [
            (0, {"A": "A", "B": "B", "X": "X", "Y": "Y"}),
            (90, {"A": "B", "B": "Y", "X": "A", "Y": "X"}),
            (180, {"A": "Y", "B": "X", "X": "B", "Y": "A"}),
            (270, {"A": "X", "B": "A", "X": "Y", "Y": "B"}),
        ],
    )
    def test_rotated(self, orientation, expected):
        for press in Press:
            rotated = {
                button.value: ButtonEvent(button, press).rotated(orientation) for button in Button
            }
            assert {name: event.button.value for name, event in rotated.items()} == expected
            assert {event.press for event in rotated.values()} == {press}

    def test_rotated_four_times_by_a_quarter_turn_is_unchanged(self):
        for button in Button:
            event = ButtonEvent(button, Press.LONG)
            turned = event
            for _ in range(4):
                turned = turned.rotated(90)
                if _ < 3:
                    assert turned != event
            assert turned == event

    def test_short_by_default(self):
        assert ButtonEvent(Button.A) == ButtonEvent(Button.A, Press.SHORT)
        assert ButtonEvent(Button.A) != ButtonEvent(Button.A, Press.LONG)

    def test_three_kinds_of_press(self):
        events = {ButtonEvent(Button.A, press) for press in Press}
        assert len(events) == 3
        assert [press.value for press in Press] == ["hold", "long", "short"]

    def test_usable_as_key(self):
        assert {ButtonEvent(Button.X): 1}[ButtonEvent(Button("X"))] == 1
