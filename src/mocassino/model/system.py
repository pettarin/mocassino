"""The host running the service: its name, its IP address, its reboot, and its shutdown.

The service itself can be restarted too.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import signal
import socket
import subprocess

# Where a UDP socket is connected to find the IP address of the host: any address outside
# the local host works, as nothing is sent
IP_PROBE_ADDRESS: tuple[str, int] = ("10.255.255.255", 1)
LOGGER: logging.Logger = logging.getLogger(__name__)
SHUTDOWN_TIMEOUT: float = 30.0
# The exit statuses of a command terminated by SIGTERM: as seen by its parent,
# and as reported by a shell or by sudo
STOPPED_RETURN_CODES: frozenset[int] = frozenset({-signal.SIGTERM, 128 + signal.SIGTERM})


class System:
    """The host running the service."""

    def __init__(
        self,
        *,
        dry_run: bool = False,
        reboot_command: tuple[str, ...],
        restart_service_command: tuple[str, ...],
        shutdown_command: tuple[str, ...],
    ) -> None:
        """Initialize the host.

        :param dry_run: if True, the reboot, restart service, and shutdown commands
                        are never run (e.g., with the simulator, not to reboot
                        or shut down the development machine)
        :param reboot_command: the command line rebooting the host
        :param restart_service_command: the command line restarting the service
        :param shutdown_command: the command line shutting down the host
        """
        self._dry_run = dry_run
        self._reboot_command = reboot_command
        self._restart_service_command = restart_service_command
        self._shutdown_command = shutdown_command

    def _run(
        self,
        command_line: tuple[str, ...],
        what: str,
        *,
        stopped_ok: bool = False,
    ) -> None:
        """Run the command line doing what is said; in a dry run, only log it.

        :param what: what the command does, e.g., "shutting down the host", for the log
        :param stopped_ok: if True, the command being terminated by SIGTERM is not a failure
        :raises SystemShutdownError: if the command cannot be run, times out, or fails
        """
        command = list(command_line)
        if self._dry_run:
            LOGGER.warning("Not %s (dry run): would run %s", what, command)
            return
        LOGGER.warning("%s with %s", what.capitalize(), command)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=SHUTDOWN_TIMEOUT,
            )
        except OSError as exc:
            raise SystemShutdownError(f"Cannot run {command}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise SystemShutdownError(f"Timeout running {command}") from exc
        if stopped_ok and result.returncode in STOPPED_RETURN_CODES:
            return
        if result.returncode != 0:
            message = result.stderr.strip() or f"exit status {result.returncode}"
            raise SystemShutdownError(f"Error running {command}: {message}")

    def hostname(self) -> str:
        """Return the name of the host."""
        return socket.gethostname()

    def ip_address(self) -> str | None:
        """Return the IP address of the host on its network, or None if it has none.

        No packet is sent: connecting a UDP socket only selects the outgoing interface.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(IP_PROBE_ADDRESS)
                return str(sock.getsockname()[0])
        except OSError:
            return None

    def reboot(self) -> None:
        """Reboot the host; in a dry run, only log the command that would be run.

        :raises SystemShutdownError: if the reboot command cannot be run, times out, or fails
        """
        self._run(self._reboot_command, "rebooting the host")

    def restart_service(self) -> None:
        """Restart the service; in a dry run, only log the command that would be run.

        The command is run by the service being restarted, so it is stopped with it:
        the command being terminated by SIGTERM is expected, and it is not a failure.

        :raises SystemShutdownError: if the restart service command cannot be run,
                                     times out, or fails
        """
        self._run(self._restart_service_command, "restarting the service", stopped_ok=True)

    def shutdown(self) -> None:
        """Shut down the host; in a dry run, only log the command that would be run.

        :raises SystemShutdownError: if the shutdown command cannot be run, times out, or fails
        """
        self._run(self._shutdown_command, "shutting down the host")


class SystemShutdownError(Exception):
    """Raised when the host cannot be shut down or rebooted, or the service restarted."""
