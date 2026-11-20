"""The state file: what the player remembers from one run to the next.

It holds the volume, and what was playing::

    playback:
      directory_path: /music/Artist/Album
      file_path: /music/Artist/Album/003_Track.flac
      seek: 95
      state: playing
      volume: 85

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mocassino.defaults import DEFAULT_STATE_FILE_PATH
from mocassino.model.moc import MocState

LOGGER: logging.Logger = logging.getLogger(__name__)
# How the playback states are written in the file
STATE_NAMES: dict[MocState, str] = {
    MocState.PAUSE: "paused",
    MocState.PLAY: "playing",
    MocState.STOP: "stopped",
}


@dataclass(frozen=True)
class SavedState:
    """The state saved in the state file.

    The directory path is what MOC was given to play: a directory or, when a single file
    was played, that file. The file path is the track that was playing, and the seek
    is the position in it, in seconds. They are None, None, and 0 when nothing was playing.
    The volume is None when it is not known.
    """

    directory_path: str | None = None
    file_path: str | None = None
    seek: int = 0
    state: MocState = MocState.STOP
    volume: int | None = None


class StateFile:
    """The YAML file where the state of the player is saved, and restored from."""

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the state file; nothing is read or written yet.

        :param path: the YAML file; if None, the default one
        """
        self._path = DEFAULT_STATE_FILE_PATH.expanduser() if path is None else path
        self._saved: dict[str, Any] | None = None

    def _content(self, state: SavedState) -> dict[str, Any]:
        """Return the given state as the content of the file."""
        return {
            "playback": {
                "directory_path": state.directory_path,
                "file_path": state.file_path,
                "seek": state.seek,
                "state": STATE_NAMES[state.state],
                "volume": state.volume,
            }
        }

    def load(self) -> SavedState:
        """Return the state saved in the file.

        What is missing or not valid takes its default value;
        a warning is logged if the file cannot be read, or has a value that is not valid.
        """
        if not self._path.exists():
            return SavedState()
        try:
            content = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            LOGGER.warning("Cannot read the state file '%s': %s", self._path, exc)
            return SavedState()
        playback = content.get("playback") if isinstance(content, dict) else None
        if not isinstance(playback, dict):
            LOGGER.warning("The state file '%s' has no playback state", self._path)
            return SavedState()
        names = {name: state for state, name in STATE_NAMES.items()}
        checks: dict[str, bool] = {
            "directory_path": _is_text(playback.get("directory_path")),
            "file_path": _is_text(playback.get("file_path")),
            "seek": _is_integer(playback.get("seek"), 0, None),
            "state": playback.get("state") in names,
            "volume": _is_integer(playback.get("volume"), 0, 100),
        }
        for key, valid in checks.items():
            if not valid and playback.get(key) is not None:
                LOGGER.warning("The state file '%s' has no valid %s", self._path, key)
        state = SavedState(
            directory_path=playback["directory_path"] if checks["directory_path"] else None,
            file_path=playback["file_path"] if checks["file_path"] else None,
            seek=playback["seek"] if checks["seek"] else 0,
            state=names[playback["state"]] if checks["state"] else MocState.STOP,
            volume=playback["volume"] if checks["volume"] else None,
        )
        if all(checks.values()):
            self._saved = self._content(state)
        return state

    @property
    def path(self) -> Path:
        """The YAML file."""
        return self._path

    def save(self, state: SavedState) -> bool:
        """Save the state to the file, unless it is the same already saved or loaded.

        The new content replaces the old one in a single step,
        so that the file is never left half-written.
        An error is logged, not raised.

        :return: whether the file has been written
        """
        content = self._content(state)
        if content == self._saved:
            return False
        temporary = self._path.with_name(f"{self._path.name}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=True),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError as exc:
            LOGGER.error("Cannot write the state file '%s': %s", self._path, exc)
            return False
        self._saved = content
        LOGGER.debug("State saved to '%s'", self._path)
        return True


def _is_integer(value: object, minimum: int, maximum: int | None) -> bool:
    """Tell whether a value is an integer (not a boolean) within the given limits."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value >= minimum and (maximum is None or value <= maximum)


def _is_text(value: object) -> bool:
    """Tell whether a value is a string that is not empty."""
    return isinstance(value, str) and value != ""
