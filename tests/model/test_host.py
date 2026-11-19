"""Tests for the host.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import socket
import subprocess

import pytest

from mocassino.model.host import SHUTDOWN_TIMEOUT, Host, HostError

COMMAND = ("sudo", "shutdown", "-h", "now")


@pytest.fixture
def run(mocker):
    """Replace subprocess.run, so that the host is never really shut down."""
    return mocker.patch(
        "mocassino.model.host.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
    )


class TestHost:
    """Tests for the Host class"""

    def test_hostname(self, mocker):
        mocker.patch("mocassino.model.host.socket.gethostname", return_value="pirate")
        assert Host(COMMAND).hostname() == "pirate"

    def test_ip_address(self, mocker):
        socket_class = mocker.patch("mocassino.model.host.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.getsockname.return_value = ("192.168.1.20", 54321)
        assert Host(COMMAND).ip_address() == "192.168.1.20"
        socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect.assert_called_once_with(("10.255.255.255", 1))

    def test_ip_address_not_available(self, mocker):
        socket_class = mocker.patch("mocassino.model.host.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.connect.side_effect = OSError("Network is unreachable")
        assert Host(COMMAND).ip_address() is None

    def test_shutdown(self, run):
        Host(COMMAND).shutdown()
        run.assert_called_once_with(
            ["sudo", "shutdown", "-h", "now"],
            capture_output=True,
            check=False,
            text=True,
            timeout=SHUTDOWN_TIMEOUT,
        )

    def test_shutdown_dry_run(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            Host(COMMAND, dry_run=True).shutdown()
        run.assert_not_called()
        assert "Not shutting down the host (dry run)" in caplog.text
        assert "['sudo', 'shutdown', '-h', 'now']" in caplog.text

    def test_shutdown_command_not_found(self, run):
        run.side_effect = FileNotFoundError("No such file or directory: 'sudo'")
        with pytest.raises(HostError, match="Cannot run"):
            Host(COMMAND).shutdown()

    def test_shutdown_fails(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="denied\n")
        with pytest.raises(HostError, match="denied"):
            Host(COMMAND).shutdown()

    def test_shutdown_fails_without_message(self, run):
        run.return_value = subprocess.CompletedProcess([], 4, stdout="", stderr="")
        with pytest.raises(HostError, match="exit status 4"):
            Host(COMMAND).shutdown()

    def test_shutdown_times_out(self, run):
        run.side_effect = subprocess.TimeoutExpired(["sudo"], SHUTDOWN_TIMEOUT)
        with pytest.raises(HostError, match="Timeout running"):
            Host(COMMAND).shutdown()
