"""mocassino -

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging

# from mocassino.clients import (...)

# The library logs under the "mocassino" logger;
# without a handler of the user's (the CLI installs its own),
# the records go nowhere, silently
logging.getLogger("mocassino").addHandler(logging.NullHandler())

__version__ = "0.0.2"
__author__ = "Alberto Pettarin"
__email__ = "alberto@albertopettarin.it"

__all__ = [
    # "symbol",
]
