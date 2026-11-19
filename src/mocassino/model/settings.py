"""The settings that can be changed while the service runs, from the settings menu.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from dataclasses import dataclass


@dataclass
class Settings:
    """The settings that can be changed while the service runs.

    Their initial values come from the configuration; the changes are not saved to it.
    """

    show_side_icons: bool = True
    use_saved_volume: bool = True
