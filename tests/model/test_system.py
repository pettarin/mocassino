"""Tests for the system: the host running the service.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import socket
import subprocess

import pytest

from mocassino.model.system import SHUTDOWN_TIMEOUT, System, SystemShutdownError

COMMAND = ("sudo", "shutdown", "-h", "now")


@pytest.fixture
def run(mocker):
    """Replace subprocess.run, so that the host is never really shut down."""
    return mocker.patch(
        "mocassino.model.system.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
    )


class TestSystem:
    """Tests for the System class"""

    def test_hostname(self, mocker):
        mocker.patch("mocassino.model.system.socket.gethostname", return_value="pirate")
        assert System(COMMAND).hostname() == "pirate"

    def test_ip_address(self, mocker):
        socket_class = mocker.patch("mocassino.model.system.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.getsockname.return_value = ("192.168.1.20", 54321)
        assert System(COMMAND).ip_address() == "192.168.1.20"
        socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect.assert_called_once_with(("10.255.255.255", 1))

    def test_ip_address_not_available(self, mocker):
        socket_class = mocker.patch("mocassino.model.system.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.connect.side_effect = OSError("Network is unreachable")
        assert System(COMMAND).ip_address() is None

    def test_shutdown(self, run):
        System(COMMAND).shutdown()
        run.assert_called_once_with(
            ["sudo", "shutdown", "-h", "now"],
            capture_output=True,
            check=False,
            text=True,
            timeout=SHUTDOWN_TIMEOUT,
        )

    def test_shutdown_dry_run(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            System(COMMAND, dry_run=True).shutdown()
        run.assert_not_called()
        assert "Not shutting down the host (dry run)" in caplog.text
        assert "['sudo', 'shutdown', '-h', 'now']" in caplog.text

    def test_shutdown_command_not_found(self, run):
        run.side_effect = FileNotFoundError("No such file or directory: 'sudo'")
        with pytest.raises(SystemShutdownError, match="Cannot run"):
            System(COMMAND).shutdown()

    def test_shutdown_fails(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="denied\n")
        with pytest.raises(SystemShutdownError, match="denied"):
            System(COMMAND).shutdown()

    def test_shutdown_fails_without_message(self, run):
        run.return_value = subprocess.CompletedProcess([], 4, stdout="", stderr="")
        with pytest.raises(SystemShutdownError, match="exit status 4"):
            System(COMMAND).shutdown()

    def test_shutdown_times_out(self, run):
        run.side_effect = subprocess.TimeoutExpired(["sudo"], SHUTDOWN_TIMEOUT)
        with pytest.raises(SystemShutdownError, match="Timeout running"):
            System(COMMAND).shutdown()
