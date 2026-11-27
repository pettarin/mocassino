"""The music library: the directories and the audio files under the music root directory.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS: tuple[str, ...] = (".flac", ".mp3", ".ogg", ".wav")
LOGGER: logging.Logger = logging.getLogger(__name__)


class Library:
    """The music library rooted at a directory."""

    def __init__(self, directory_path: Path) -> None:
        """Initialize the library.

        :param directory_path: the music root directory
        """
        self._directory_path = directory_path

    @property
    def directory_path(self) -> Path:
        """The music root directory."""
        return self._directory_path

    @directory_path.setter
    def directory_path(self, directory_path: Path) -> None:
        self._directory_path = directory_path

    def list_entries(self, directory_path: Path | None = None) -> list[LibraryEntry]:
        """List the subdirectories and the audio files of a directory of the library.

        The subdirectories come first; both groups are sorted by name, ignoring the case.
        Hidden entries and files that are not audio files are skipped.
        A directory that cannot be read is reported as empty.

        :param directory_path: the directory to list; if None, the music root directory
        :raises ValueError: if the directory is outside the music root directory
        """
        directory_path = directory_path or self._directory_path
        if not directory_path.is_relative_to(self._directory_path):
            raise ValueError(f"'{directory_path}' is outside '{self._directory_path}'")
        try:
            children = list(directory_path.iterdir())
        except OSError as exc:
            LOGGER.warning("Cannot list '%s': %s", directory_path, exc)
            return []
        entries: list[LibraryEntry] = []
        for child in children:
            if child.name.startswith("."):
                continue
            if child.is_dir():
                entries.append(LibraryEntry(is_directory=True, name=child.name, path=child))
            elif child.is_file() and child.suffix.lower() in AUDIO_EXTENSIONS:
                entries.append(LibraryEntry(is_directory=False, name=child.name, path=child))
        return sorted(
            entries,
            key=lambda entry: (not entry.is_directory, entry.name.casefold(), entry.name),
        )


@dataclass(frozen=True)
class LibraryEntry:
    """A subdirectory or an audio file of the library."""

    is_directory: bool
    name: str
    path: Path


def list_directories(directory_path: Path) -> list[Path]:
    """List the subdirectories of a directory, which can be anywhere on the host.

    They are sorted by name, ignoring the case, and the hidden ones are skipped.
    A directory that cannot be read is reported as having none.
    """
    try:
        directories = [
            child
            for child in directory_path.iterdir()
            if not child.name.startswith(".") and child.is_dir()
        ]
    except OSError as exc:
        LOGGER.warning("Cannot list '%s': %s", directory_path, exc)
        return []
    return sorted(directories, key=lambda child: (child.name.casefold(), child.name))
