"""The host running the service: its name, its IP address, and its shutdown.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import socket
import subprocess

LOGGER: logging.Logger = logging.getLogger(__name__)
SHUTDOWN_TIMEOUT: float = 30.0


class Host:
    """The host running the service."""

    def __init__(self, shutdown_command: tuple[str, ...]) -> None:
        """Initialize the host.

        :param shutdown_command: the command line shutting down the host
        """
        self._shutdown_command = shutdown_command

    def hostname(self) -> str:
        """Return the name of the host."""
        return socket.gethostname()

    def ip_address(self) -> str | None:
        """Return the IP address of the host on its network, or None if it has none.

        No packet is sent: connecting a UDP socket only selects the outgoing interface.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("10.255.255.255", 1))
                return str(sock.getsockname()[0])
        except OSError:
            return None

    def shutdown(self) -> None:
        """Shut down the host.

        :raises HostError: if the shutdown command cannot be run, times out, or fails
        """
        command = list(self._shutdown_command)
        LOGGER.warning("Shutting down the host with %s", command)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=SHUTDOWN_TIMEOUT,
            )
        except OSError as exc:
            raise HostError(f"Cannot run {command}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise HostError(f"Timeout running {command}") from exc
        if result.returncode != 0:
            message = result.stderr.strip() or f"exit status {result.returncode}"
            raise HostError(f"Error running {command}: {message}")


class HostError(Exception):
    """Raised when the host cannot be shut down."""
