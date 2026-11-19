"""Client of MOC (music on console): the playback is fully delegated to it.

The client talks to the MOC server by running ``mocp`` commands via subprocess.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

# When the MOC server is busy, it may refuse a command: the command is then tried again,
# for this many times in all, this far apart (in seconds)
BUSY_ATTEMPTS: int = 3
BUSY_INTERVAL: float = 0.05
BUSY_MESSAGE: str = "Can't connect to the server"
DEFAULT_TIMEOUT: float = 5.0
LOGGER: logging.Logger = logging.getLogger(__name__)
SERVER_ALREADY_RUNNING_MESSAGE: str = "Server is already running"
SERVER_NOT_RUNNING_MESSAGE: str = "The server is not running"


class MocClient(Protocol):
    """What the service needs from MOC."""

    def jump(self, seconds: int) -> None:
        """Jump to the given position, in seconds, in the track being played."""

    def load(self, path: Path) -> None:
        """Replace the playlist with the given file or directory, without playing it."""

    def next(self) -> None:
        """Play the next track of the playlist."""

    def pause(self) -> None:
        """Pause the playback."""

    def play(self, path: Path) -> None:
        """Replace the playlist with the given file or directory, and play it."""

    def play_playlist(self) -> None:
        """Play the playlist, from its first track."""

    def previous(self) -> None:
        """Play the previous track of the playlist."""

    def seek(self, seconds: int) -> None:
        """Seek by the given number of seconds: forward if positive, backward if negative."""

    def set_volume(self, level: int) -> None:
        """Set the volume to the given level, between 0 and 100."""

    def start_server(self) -> None:
        """Start the MOC server, if it is not already running."""

    def status(self) -> MocStatus:
        """Return the current playback status."""

    def stop(self) -> None:
        """Stop the playback."""

    def toggle_pause(self) -> None:
        """Toggle between playing and paused."""

    def unpause(self) -> None:
        """Resume the paused playback."""


class MocError(Exception):
    """Raised when a MOC command fails."""


class MocServerNotRunningError(MocError):
    """Raised when a MOC command fails because the MOC server is not running."""


class MocState(StrEnum):
    """The playback state reported by MOC."""

    PAUSE = "PAUSE"
    PLAY = "PLAY"
    STOP = "STOP"


@dataclass(frozen=True)
class MocStatus:
    """The playback status reported by MOC.

    The total number of seconds is None when MOC does not know it
    (e.g., for a network stream).
    """

    album: str = ""
    artist: str = ""
    current_seconds: int = 0
    file_path: str = ""
    state: MocState = MocState.STOP
    title: str = ""
    total_seconds: int | None = None


class SubprocessMocClient:
    """MOC client running ``mocp`` commands via subprocess."""

    def __init__(self, mocp_file_path: str = "mocp", timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize the client.

        :param mocp_file_path: the ``mocp`` executable
        :param timeout: the maximum duration of a command, in seconds
        """
        self._mocp_file_path = mocp_file_path
        self._timeout = timeout

    def _run(self, *arguments: str) -> str:
        """Run a ``mocp`` command and return its standard output.

        A command refused because the MOC server is busy is tried again a few times.

        :raises MocServerNotRunningError: if the MOC server is not running
        :raises MocError: if the command cannot be run, times out, or fails
        """
        command = [self._mocp_file_path, *arguments]
        LOGGER.debug("Running %s", command)
        message = ""
        for attempt in range(BUSY_ATTEMPTS):
            if attempt > 0:
                time.sleep(BUSY_INTERVAL)
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=self._timeout,
                )
            except OSError as exc:
                raise MocError(f"Cannot run {command}: {exc}") from exc
            except subprocess.TimeoutExpired as exc:
                raise MocError(f"Timeout running {command}") from exc
            if result.returncode == 0:
                return result.stdout
            message = result.stderr.strip() or f"exit status {result.returncode}"
            if BUSY_MESSAGE not in message:
                break
        if SERVER_NOT_RUNNING_MESSAGE in message:
            raise MocServerNotRunningError(message)
        raise MocError(f"Error running {command}: {message}")

    def jump(self, seconds: int) -> None:
        """Jump to the given position, in seconds, in the track being played."""
        self._run(f"--jump={seconds}s")

    def load(self, path: Path) -> None:
        """Replace the playlist with the given file or directory, without playing it."""
        self._run("--clear")
        self._run("--append", str(path))

    def next(self) -> None:
        """Play the next track of the playlist."""
        self._run("--next")

    def pause(self) -> None:
        """Pause the playback."""
        self._run("--pause")

    def play(self, path: Path) -> None:
        """Replace the playlist with the given file or directory, and play it."""
        self.load(path)
        self._run("--play")

    def play_playlist(self) -> None:
        """Play the playlist, from its first track."""
        self._run("--play")

    def previous(self) -> None:
        """Play the previous track of the playlist."""
        self._run("--previous")

    def seek(self, seconds: int) -> None:
        """Seek by the given number of seconds: forward if positive, backward if negative."""
        self._run(f"--seek={seconds}")

    def set_volume(self, level: int) -> None:
        """Set the volume to the given level, between 0 and 100."""
        if not 0 <= level <= 100:
            raise ValueError(f"The volume level must be between 0 and 100: {level}")
        self._run(f"--volume={level}")

    def start_server(self) -> None:
        """Start the MOC server, if it is not already running."""
        try:
            self._run("--server")
        except MocError as exc:
            if SERVER_ALREADY_RUNNING_MESSAGE not in str(exc):
                raise

    def status(self) -> MocStatus:
        """Return the current playback status."""
        return parse_status(self._run("--info"))

    def stop(self) -> None:
        """Stop the playback."""
        self._run("--stop")

    def toggle_pause(self) -> None:
        """Toggle between playing and paused."""
        self._run("--toggle-pause")

    def unpause(self) -> None:
        """Resume the paused playback."""
        self._run("--unpause")


def parse_status(output: str) -> MocStatus:
    """Parse the output of ``mocp --info``.

    The output has one ``Key: value`` pair per line; when the playback is stopped,
    it has the ``State`` line only.

    :raises MocError: if the state or a number of seconds cannot be parsed
    """
    values: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    try:
        total_seconds = int(values["TotalSec"]) if "TotalSec" in values else None
        return MocStatus(
            album=values.get("Album", ""),
            artist=values.get("Artist", ""),
            current_seconds=max(0, int(values.get("CurrentSec", "0"))),
            file_path=values.get("File", ""),
            state=MocState(values.get("State", "")),
            title=values.get("SongTitle", ""),
            total_seconds=total_seconds,
        )
    except ValueError as exc:
        raise MocError(f"Cannot parse the MOC status: {exc}") from exc
