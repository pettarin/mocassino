"""Fixtures shared by all the tests.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest


@pytest.fixture(autouse=True)
def no_real_commands(mocker):
    """Make the tests fail, instead of running a real command, if they reach MOC or the host.

    The tests that need those commands replace them explicitly, on top of this.
    """

    def refuse(command, *args, **kwargs):
        raise AssertionError(f"A test tried to run a real command: {command}")

    mocker.patch("mocassino.model.system.subprocess.run", side_effect=refuse)
    mocker.patch("mocassino.model.moc.subprocess.run", side_effect=refuse)
