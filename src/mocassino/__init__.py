"""mocassino - Lightweight audio player based on MOC for Raspberry Pi Zero 2
               devices with Pimoroni Pirate Audio hats

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

# The library logs under the "mocassino" logger;
# without a handler of the user's (the CLI installs its own),
# the records go nowhere, silently
logging.getLogger("mocassino").addHandler(logging.NullHandler())

__version__ = "0.0.5"
__author__ = "Alberto Pettarin"
__email__ = "alberto@albertopettarin.it"

