"""Font resources for mocassino.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from importlib.resources import files
from pathlib import Path

# The font used when none is configured: Roboto Regular,
# licensed under the SIL Open Font License 1.1 (see the OFL.txt file next to it)
ROBOTO_REGULAR_FILE_PATH: Path = Path(str(files(__name__).joinpath("Roboto-Regular.ttf")))
