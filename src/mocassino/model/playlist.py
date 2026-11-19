"""The playlist of MOC: its tracks, and how far the playback has advanced through them.

MOC does not tell where the current track is in its playlist,
so the playlist is rebuilt from what MOC was given to play, as MOC builds it:
a directory gives all the audio files under it, recursively, sorted by their full path.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
from collections.abc import Sequence
from pathlib import Path

from mocassino.model.library import AUDIO_EXTENSIONS
from mocassino.model.moc import MocStatus

LOGGER: logging.Logger = logging.getLogger(__name__)


def list_tracks(path: Path) -> tuple[str, ...]:
    """Return the tracks MOC plays when given the path, in the order it plays them.

    A file is a playlist of its own. A directory gives the audio files under it,
    recursively, sorted by their full path; hidden files and directories are skipped,
    and so are the directories that cannot be read.

    :param path: a directory or a file
    :return: the full paths of the tracks; none if the path is neither a directory nor a file
    """
    if path.is_file():
        return (str(path),)
    if not path.is_dir():
        return ()
    tracks: list[str] = []

    def on_error(error: OSError) -> None:
        LOGGER.warning("Cannot list '%s': %s", error.filename, error)

    for directory, subdirectories, files in os.walk(path, onerror=on_error):
        subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
        tracks.extend(
            os.path.join(directory, name)
            for name in files
            if not name.startswith(".") and Path(name).suffix.lower() in AUDIO_EXTENSIONS
        )
    return tuple(sorted(tracks))


def playlist_fraction(playlist: Sequence[str], status: MocStatus) -> float:
    """Return how far the playback has advanced through the playlist, between 0.0 and 1.0.

    The current track counts as done, together with those before it:
    the fraction is 1.0 while the last track is played, telling that it is the last one.

    :param playlist: the tracks, in the order they are played
    :param status: the status of MOC
    :return: the fraction; 0.0 if the current track is not in the playlist (e.g., nothing
             is playing, or a network stream is)
    """
    if status.file_path not in playlist:
        return 0.0
    return (playlist.index(status.file_path) + 1) / len(playlist)
