"""Tests for the button source interface.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.controller.buttons.base import ButtonSource
from mocassino.controller.buttons.gpio import GpioButtonSource
from mocassino.controller.buttons.null import NullButtonSource


class TestButtonSource:
    """Tests for the ButtonSource protocol"""

    @pytest.mark.parametrize("source_class", [GpioButtonSource, NullButtonSource])
    def test_implementations(self, source_class):
        methods = [name for name in vars(ButtonSource) if not name.startswith("_")]
        assert sorted(methods) == ["close", "set_pin_button_y", "start"]
        for name in methods:
            assert callable(getattr(source_class, name))
