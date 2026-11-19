"""Tests for the MOC client.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import subprocess
from pathlib import Path

import pytest

from mocassino.model.moc import (
    MocError,
    MocServerNotRunningError,
    MocState,
    MocStatus,
    SubprocessMocClient,
    parse_status,
)

# The format follows interface_cmdline_file_info() in the interface.c file of MOC
INFO_PLAY = (
    "State: PLAY\n"
    "File: /music/Artist/Album/01 - Intro: Part 1.flac\n"
    "Title: 1 Artist - Intro: Part 1 (Album)\n"
    "Artist: Artist\n"
    "SongTitle: Intro: Part 1\n"
    "Album: Album\n"
    "TotalTime: 03:25\n"
    "TimeLeft: 02:15\n"
    "TotalSec: 205\n"
    "CurrentTime: 01:10\n"
    "CurrentSec: 70\n"
    "Bitrate: 912kbps\n"
    "AvgBitrate: 905kbps\n"
    "Rate: 44kHz\n"
)
INFO_STOP = "State: STOP\n"
INFO_UNTAGGED_STREAM = (
    "State: PAUSE\n"
    "File: http://example.com/stream\n"
    "Title: \n"
    "Artist: \n"
    "SongTitle: \n"
    "Album: \n"
    "CurrentTime: 00:00\n"
    "CurrentSec: -1\n"
    "Bitrate: 0kbps\n"
    "AvgBitrate: 0kbps\n"
    "Rate: 0kHz\n"
)


def completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Build the result of a mocp command."""
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def run(mocker):
    """Replace subprocess.run, so that mocp is never really run."""
    return mocker.patch("mocassino.model.moc.subprocess.run", return_value=completed())


def commands(run) -> list[list[str]]:
    """Return the commands passed to subprocess.run, in order."""
    return [call.args[0] for call in run.call_args_list]


class TestParseStatus:
    """Tests for the parse_status function"""

    def test_empty(self):
        with pytest.raises(MocError, match="Cannot parse the MOC status"):
            parse_status("")

    def test_invalid_seconds(self):
        with pytest.raises(MocError, match="Cannot parse the MOC status"):
            parse_status("State: PLAY\nCurrentSec: soon\n")

    def test_invalid_state(self):
        with pytest.raises(MocError, match="Cannot parse the MOC status"):
            parse_status("State: REWIND\n")

    def test_play(self):
        assert parse_status(INFO_PLAY) == MocStatus(
            album="Album",
            artist="Artist",
            current_seconds=70,
            file_path="/music/Artist/Album/01 - Intro: Part 1.flac",
            state=MocState.PLAY,
            title="Intro: Part 1",
            total_seconds=205,
        )

    def test_stop(self):
        assert parse_status(INFO_STOP) == MocStatus(state=MocState.STOP)

    def test_untagged_stream(self):
        assert parse_status(INFO_UNTAGGED_STREAM) == MocStatus(
            current_seconds=0,
            file_path="http://example.com/stream",
            state=MocState.PAUSE,
            total_seconds=None,
        )


class TestSubprocessMocClient:
    """Tests for the SubprocessMocClient class"""

    def test_command_fails(self, run):
        run.return_value = completed(returncode=2, stderr="\nFATAL_ERROR: Can't send command!\n")
        with pytest.raises(MocError, match="FATAL_ERROR: Can't send command!") as info:
            SubprocessMocClient().stop()
        assert not isinstance(info.value, MocServerNotRunningError)

    def test_command_fails_without_message(self, run):
        run.return_value = completed(returncode=3)
        with pytest.raises(MocError, match="exit status 3"):
            SubprocessMocClient().stop()

    def test_command_not_found(self, run):
        run.side_effect = FileNotFoundError("No such file or directory: 'mocp'")
        with pytest.raises(MocError, match="Cannot run"):
            SubprocessMocClient().stop()

    def test_command_options(self, run):
        SubprocessMocClient(mocp_file_path="/opt/mocp", timeout=2.5).stop()
        run.assert_called_once_with(
            ["/opt/mocp", "--stop"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2.5,
        )

    def test_command_times_out(self, run):
        run.side_effect = subprocess.TimeoutExpired(["mocp"], 5.0)
        with pytest.raises(MocError, match="Timeout running"):
            SubprocessMocClient().stop()

    def test_next(self, run):
        SubprocessMocClient().next()
        assert commands(run) == [["mocp", "--next"]]

    def test_play(self, run):
        SubprocessMocClient().play(Path("/music/Artist/Album"))
        assert commands(run) == [
            ["mocp", "--clear"],
            ["mocp", "--append", "/music/Artist/Album"],
            ["mocp", "--play"],
        ]

    def test_play_playlist(self, run):
        SubprocessMocClient().play_playlist()
        assert commands(run) == [["mocp", "--play"]]

    def test_previous(self, run):
        SubprocessMocClient().previous()
        assert commands(run) == [["mocp", "--previous"]]

    def test_server_not_running(self, run):
        run.return_value = completed(
            returncode=2,
            stderr="\nFATAL_ERROR: The server is not running!\n",
        )
        with pytest.raises(MocServerNotRunningError, match="The server is not running"):
            SubprocessMocClient().status()

    def test_set_volume(self, run):
        SubprocessMocClient().set_volume(35)
        assert commands(run) == [["mocp", "--volume=35"]]

    @pytest.mark.parametrize("level", [-1, 101])
    def test_set_volume_out_of_range(self, run, level):
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            SubprocessMocClient().set_volume(level)
        run.assert_not_called()

    def test_start_server(self, run):
        SubprocessMocClient().start_server()
        assert commands(run) == [["mocp", "--server"]]

    def test_start_server_already_running(self, run):
        run.return_value = completed(
            returncode=2,
            stderr="\nFATAL_ERROR: Server is already running!\n",
        )
        SubprocessMocClient().start_server()
        assert commands(run) == [["mocp", "--server"]]

    def test_start_server_fails(self, run):
        run.return_value = completed(returncode=2, stderr="\nFATAL_ERROR: Server exited!\n")
        with pytest.raises(MocError, match="Server exited"):
            SubprocessMocClient().start_server()

    def test_status(self, run):
        run.return_value = completed(stdout=INFO_PLAY)
        status = SubprocessMocClient().status()
        assert commands(run) == [["mocp", "--info"]]
        assert status.state == MocState.PLAY
        assert status.title == "Intro: Part 1"

    def test_stop(self, run):
        SubprocessMocClient().stop()
        assert commands(run) == [["mocp", "--stop"]]

    def test_toggle_pause(self, run):
        SubprocessMocClient().toggle_pause()
        assert commands(run) == [["mocp", "--toggle-pause"]]
