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
REBOOT = ("sudo", "reboot")
RESTART_SERVICE = ("sudo", "systemctl", "restart", "mocassino.service")


def make_system(dry_run: bool = False) -> System:
    """Return a system with the test commands."""
    return System(
        dry_run=dry_run,
        reboot_command=REBOOT,
        restart_service_command=RESTART_SERVICE,
        shutdown_command=COMMAND,
    )


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
        assert make_system().hostname() == "pirate"

    def test_ip_address(self, mocker):
        socket_class = mocker.patch("mocassino.model.system.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.getsockname.return_value = ("192.168.1.20", 54321)
        assert make_system().ip_address() == "192.168.1.20"
        socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect.assert_called_once_with(("10.255.255.255", 1))

    def test_ip_address_not_available(self, mocker):
        socket_class = mocker.patch("mocassino.model.system.socket.socket")
        sock = socket_class.return_value.__enter__.return_value
        sock.connect.side_effect = OSError("Network is unreachable")
        assert make_system().ip_address() is None

    def test_reboot(self, run):
        make_system().reboot()
        run.assert_called_once_with(
            ["sudo", "reboot"],
            capture_output=True,
            check=False,
            text=True,
            timeout=SHUTDOWN_TIMEOUT,
        )

    def test_reboot_dry_run(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            make_system(dry_run=True).reboot()
        run.assert_not_called()
        assert "Not rebooting the host (dry run): would run ['sudo', 'reboot']" in caplog.text

    def test_reboot_fails(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="denied\n")
        with pytest.raises(SystemShutdownError, match="denied"):
            make_system().reboot()

    def test_restart_service(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            make_system().restart_service()
        assert "Restarting the service with" in caplog.text
        run.assert_called_once_with(
            ["sudo", "systemctl", "restart", "mocassino.service"],
            capture_output=True,
            check=False,
            text=True,
            timeout=SHUTDOWN_TIMEOUT,
        )

    def test_restart_service_dry_run(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            make_system(dry_run=True).restart_service()
        run.assert_not_called()
        assert "Not restarting the service (dry run): would run" in caplog.text
        assert "['sudo', 'systemctl', 'restart', 'mocassino.service']" in caplog.text

    def test_restart_service_fails(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="denied\n")
        with pytest.raises(SystemShutdownError, match="denied"):
            make_system().restart_service()

    @pytest.mark.parametrize("return_code", [-15, 143])
    def test_restart_service_stopped_with_the_service(self, run, return_code):
        run.return_value = subprocess.CompletedProcess([], return_code, stdout="", stderr="")
        make_system().restart_service()
        run.assert_called_once()

    def test_shutdown(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            make_system().shutdown()
        assert "Shutting down the host with" in caplog.text
        run.assert_called_once_with(
            ["sudo", "shutdown", "-h", "now"],
            capture_output=True,
            check=False,
            text=True,
            timeout=SHUTDOWN_TIMEOUT,
        )

    def test_shutdown_dry_run(self, run, caplog):
        with caplog.at_level(logging.WARNING):
            make_system(dry_run=True).shutdown()
        run.assert_not_called()
        assert "Not shutting down the host (dry run)" in caplog.text
        assert "['sudo', 'shutdown', '-h', 'now']" in caplog.text

    def test_shutdown_command_not_found(self, run):
        run.side_effect = FileNotFoundError("No such file or directory: 'sudo'")
        with pytest.raises(SystemShutdownError, match="Cannot run"):
            make_system().shutdown()

    def test_shutdown_fails(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="denied\n")
        with pytest.raises(SystemShutdownError, match="denied"):
            make_system().shutdown()

    def test_shutdown_fails_without_message(self, run):
        run.return_value = subprocess.CompletedProcess([], 4, stdout="", stderr="")
        with pytest.raises(SystemShutdownError, match="exit status 4"):
            make_system().shutdown()

    @pytest.mark.parametrize("return_code", [-15, 143])
    def test_shutdown_stopped_is_a_failure(self, run, return_code):
        run.return_value = subprocess.CompletedProcess([], return_code, stdout="", stderr="")
        with pytest.raises(SystemShutdownError, match=f"exit status {return_code}"):
            make_system().shutdown()

    def test_shutdown_times_out(self, run):
        run.side_effect = subprocess.TimeoutExpired(["sudo"], SHUTDOWN_TIMEOUT)
        with pytest.raises(SystemShutdownError, match="Timeout running"):
            make_system().shutdown()
