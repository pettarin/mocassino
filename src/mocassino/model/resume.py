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


def adopt_playback(moc: MocClient, saved: SavedState) -> str | None:
    """Tell what MOC is playing from, without asking anything of MOC other than its status.

    :return: the saved directory path, if MOC is playing a file inside it; otherwise,
             the directory of the file it is playing; None if MOC is stopped
    :raises MocError: if the MOC status cannot be asked
    """
    status = moc.status()
    if status.state is MocState.STOP:
        return None
    return playing_from(saved.directory_path, status.file_path)


def apply_state(moc: MocClient, state: MocState) -> None:
    """Bring what MOC has in its playlist to the given state: playing, paused, or stopped.

    Asking for a pause when MOC is stopped does nothing, as there is nothing to pause.

    :raises MocError: if a MOC command fails
    """
    current = moc.status().state
    if state is MocState.STOP and current is not MocState.STOP:
        moc.stop()
    elif state is MocState.PAUSE and current is MocState.PLAY:
        moc.pause()
    elif state is MocState.PLAY and current is MocState.PAUSE:
        moc.unpause()
    elif state is MocState.PLAY and current is MocState.STOP:
        moc.play_playlist()


def load_playback(moc: MocClient, saved: SavedState) -> str | None:
    """Give MOC the saved playback as its playlist, without playing it.

    :return: what MOC has been given (the saved directory, or that of the saved track),
             or None if there is no saved track, or it no longer exists
    :raises MocError: if a MOC command fails
    """
    file_path = saved.file_path
    directory_path = None if file_path is None else playing_from(saved.directory_path, file_path)
    if directory_path is None or file_path is None or not Path(file_path).is_file():
        return None
    moc.load(Path(directory_path))
    return directory_path


def playing_from(played_path: str | None, file_path: str) -> str | None:
    """Tell what a track is being played from.

    That is what MOC was given to play, when known and when the track is inside it
    (or is it). Otherwise (e.g., MOC was not given it by this service), it is taken to be
    the directory of the track.

    :param played_path: what MOC was given to play (a directory, or a single file), if known
    :param file_path: the track
    :return: the path, or None if the track is not a file (e.g., it is a network stream)
    """
    if played_path is not None and Path(file_path).is_relative_to(played_path):
        return played_path
    if not file_path.startswith("/"):
        return None
    return str(Path(file_path).parent)


def resume_playback(
    moc: MocClient,
    saved: SavedState,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Resume the saved playback, if MOC is stopped and what was playing still exists.

    If MOC is already playing or paused, it is left alone.
    If the saved directory is missing, or the saved track is not inside it,
    the directory of the saved track is played.
    Otherwise the saved directory (or single file) is played from its start with
    the volume at zero, the tracks before the saved one are skipped,
    the saved position is reached, and the playback is paused if it was.
    If the saved track cannot be reached, or a MOC command fails, the playback is stopped;
    if only the saved position cannot be reached, the track is resumed from its start.

    :return: what MOC is playing from, if the playback has been resumed or MOC was
             already playing; None otherwise
    :raises MocError: if a MOC command fails
    """
    file_path = saved.file_path
    directory_path = None if file_path is None else playing_from(saved.directory_path, file_path)
    if directory_path is None or file_path is None:
        return None
    if moc.status().state is not MocState.STOP:
        LOGGER.info("MOC is already playing: the saved playback is not resumed")
        return adopt_playback(moc, saved)
    if saved.state is MocState.STOP:
        return None
    if not Path(file_path).is_file():
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
