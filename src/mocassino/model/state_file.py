"""The state file: what the player remembers from one run to the next.

For now, it only holds the volume::

    playback:
      volume: 85

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from pathlib import Path
from typing import Any

import yaml

DEFAULT_STATE_FILE_PATH: Path = Path("~/.config/mocassino/state.yaml")
LOGGER: logging.Logger = logging.getLogger(__name__)


class StateFile:
    """The YAML file where the state of the player is saved, and restored from."""

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the state file; nothing is read or written yet.

        :param path: the YAML file; if None, the default one
        """
        self._path = DEFAULT_STATE_FILE_PATH.expanduser() if path is None else path
        self._saved: dict[str, Any] | None = None

    def load_volume(self) -> int | None:
        """Return the volume saved in the file, between 0 and 100.

        :return: None if the file does not exist, cannot be read, or has no valid volume;
                 except when the file does not exist, a warning is logged
        """
        if not self._path.exists():
            return None
        try:
            content = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            LOGGER.warning("Cannot read the state file '%s': %s", self._path, exc)
            return None
        playback = content.get("playback") if isinstance(content, dict) else None
        volume = playback.get("volume") if isinstance(playback, dict) else None
        if isinstance(volume, bool) or not isinstance(volume, int) or not 0 <= volume <= 100:
            LOGGER.warning("The state file '%s' has no valid volume", self._path)
            return None
        self._saved = {"playback": {"volume": volume}}
        return volume

    @property
    def path(self) -> Path:
        """The YAML file."""
        return self._path

    def save(self, volume: int) -> bool:
        """Save the state to the file, unless it is the same already saved or loaded.

        The new content replaces the old one in a single step,
        so that the file is never left half-written.
        An error is logged, not raised.

        :param volume: the volume, between 0 and 100
        :return: whether the file has been written
        """
        content = {"playback": {"volume": volume}}
        if content == self._saved:
            return False
        temporary = self._path.with_name(f"{self._path.name}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(yaml.safe_dump(content, sort_keys=True), encoding="utf-8")
            temporary.replace(self._path)
        except OSError as exc:
            LOGGER.error("Cannot write the state file '%s': %s", self._path, exc)
            return False
        self._saved = content
        LOGGER.debug("State saved to '%s'", self._path)
        return True
