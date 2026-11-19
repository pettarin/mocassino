"""Resuming the playback saved in the state file, when the player starts.

MOC cannot start a playlist from a given track: it is started from its first track,
and then MOC is asked for the next track until the saved one is reached.
Skipping a track makes MOC play it for a moment, so the volume is set to zero meanwhile:
whoever asks to resume has to set the volume afterwards.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from mocassino.model.moc import MocClient, MocError, MocState, MocStatus
from mocassino.model.state_file import SavedState

LOGGER: logging.Logger = logging.getLogger(__name__)
# At most this many tracks are skipped to reach the saved one
MAX_SKIPS: int = 1000
# After asking MOC to change track, its status is asked at most this many times,
# this far apart (in seconds), until it reports another track
POLL_ATTEMPTS: int = 40
POLL_INTERVAL: float = 0.05
# MOC may ignore a jump asked right after a change of track: it is asked again,
# for this many times in all, until the position is this close (in seconds) to the saved one
SEEK_ATTEMPTS: int = 5
SEEK_TOLERANCE: int = 3


def _seek_to(moc: MocClient, seconds: int, sleep: Callable[[float], None]) -> bool:
    """Ask MOC to jump to the given position, until it is there.

    :return: whether the position has been reached
    """
    for _ in range(SEEK_ATTEMPTS):
        moc.jump(seconds)
        sleep(POLL_INTERVAL)
        if abs(moc.status().current_seconds - seconds) <= SEEK_TOLERANCE:
            return True
    return False


def _skip_to(moc: MocClient, file_path: str, sleep: Callable[[float], None]) -> bool:
    """Ask MOC for the next track until the given one is playing.

    :return: whether the track has been reached
    """
    seen: set[str] = set()
    previous = ""
    for _ in range(MAX_SKIPS):
        status = _wait_for_track(moc, previous, sleep)
        current = status.file_path
        if status.state is MocState.STOP or current == previous or current in seen:
            return False
        if current == file_path:
            return True
        seen.add(current)
        previous = current
        moc.next()
    return False


def _wait_for_track(moc: MocClient, previous: str, sleep: Callable[[float], None]) -> MocStatus:
    """Wait until MOC plays a track other than the given one, and return its status.

    If that does not happen in time, the last status is returned.
    """
    status = moc.status()
    for _ in range(POLL_ATTEMPTS - 1):
        if status.state is not MocState.STOP and status.file_path != previous:
            break
        sleep(POLL_INTERVAL)
        status = moc.status()
    return status


def resume_playback(
    moc: MocClient,
    saved: SavedState,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Resume the saved playback, if MOC is stopped and what was playing still exists.

    If MOC is already playing or paused, it is left alone.
    Otherwise the saved directory (or single file) is played from its start with
    the volume at zero, the tracks before the saved one are skipped,
    the saved position is reached, and the playback is paused if it was.
    If the saved track cannot be reached, or a MOC command fails, the playback is stopped;
    if only the saved position cannot be reached, the track is resumed from its start.

    :return: what MOC is playing from: the saved directory path if the playback has been
             resumed, or if MOC was already playing a file inside it; None otherwise
    :raises MocError: if a MOC command fails
    """
    directory_path, file_path = saved.directory_path, saved.file_path
    if directory_path is None or file_path is None:
        return None
    status = moc.status()
    if status.state is not MocState.STOP:
        inside = Path(status.file_path).is_relative_to(directory_path)
        LOGGER.info("MOC is already playing: the saved playback is not resumed")
        return directory_path if inside else None
    if saved.state is MocState.STOP:
        return None
    if not Path(file_path).is_file() or not Path(file_path).is_relative_to(directory_path):
        LOGGER.warning("The saved track '%s' cannot be resumed", file_path)
        return None
    LOGGER.info("Resuming '%s' at %d seconds", file_path, saved.seek)
    moc.set_volume(0)
    try:
        moc.play(Path(directory_path))
        if not _skip_to(moc, file_path, sleep):
            LOGGER.warning("The saved track '%s' is not in '%s'", file_path, directory_path)
            moc.stop()
            return None
        if saved.seek > 0 and not _seek_to(moc, saved.seek, sleep):
            LOGGER.warning("The saved position of '%s' cannot be reached", file_path)
        if saved.state is MocState.PAUSE:
            moc.pause()
    except MocError:
        moc.stop()
        raise
    return directory_path
