"""Command line interface of mocassino.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
import shutil
import signal
import sys
import threading
from dataclasses import dataclass, replace
from logging.handlers import SysLogHandler
from pathlib import Path
from types import FrameType

import click
import yaml

from mocassino import __version__
from mocassino.app import App, build_app
from mocassino.configuration import (
    Configuration,
    ConfigurationError,
    ConfigurationReadError,
    load_configuration,
    replace_invalid_configuration_file,
    simulated_defaults,
)
from mocassino.constants import ORIENTATIONS, ButtonsOrigin, DisplayTarget, RunMode
from mocassino.defaults import DEFAULT_CONFIGURATION_FILE_PATH
from mocassino.simulator.tk import TkSimulator

LOGGER: logging.Logger = logging.getLogger(__name__)
SYSLOG_SOCKET_PATH: Path = Path("/dev/log")


@dataclass(frozen=True)
class GlobalOptions:
    """The options given before the command, shared by all the commands.

    They select and override the configuration.
    """

    buttons_origin: str | None
    configuration_file_path: Path | None
    display_target: str | None
    library_directory_path: Path | None
    simulator: bool
    state_file_path: Path | None


def _daemonize() -> None:
    """Continue in a background process, detached from the terminal.

    The process in the foreground prints the identifier of the one in background and exits.
    The process in background closes all the files inherited from the one in foreground,
    so that whoever launched it is not kept waiting.
    It has no terminal to write its log messages to,
    so it sends them to the system log instead, if available.
    """
    pid = os.fork()
    if pid > 0:
        click.echo(f"mocassino is running in background (PID {pid})")
        sys.exit(0)
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for descriptor in (0, 1, 2):
        os.dup2(null, descriptor)
    os.close(null)
    os.closerange(3, os.sysconf("SC_OPEN_MAX"))
    handlers: list[logging.Handler] = []
    if SYSLOG_SOCKET_PATH.exists():
        handler = SysLogHandler(address=str(SYSLOG_SOCKET_PATH))
        handler.setFormatter(logging.Formatter("mocassino: %(levelname)s %(name)s: %(message)s"))
        handlers.append(handler)
    logging.getLogger().handlers = handlers


def _load_configuration(options: GlobalOptions, recover: bool = False) -> Configuration:
    """Load the configuration, reporting the errors as command line errors.

    :param recover: if True, a configuration file that is not valid is replaced
                    with one with the default values (see _recover_configuration_file)
    """
    buttons_origin, display_target = options.buttons_origin, options.display_target
    if options.simulator:
        buttons_origin = buttons_origin or ButtonsOrigin.SIMULATOR.value
        display_target = display_target or DisplayTarget.SIMULATOR.value
    overrides = {
        "buttons": {"origin": buttons_origin},
        "display": {"target": display_target},
        "library": {"directory_path": options.library_directory_path},
    }
    path = options.configuration_file_path
    try:
        return load_configuration(path, overrides)
    except ConfigurationError as exc:
        simulated = (
            buttons_origin == ButtonsOrigin.SIMULATOR,
            display_target == DisplayTarget.SIMULATOR,
        )
        if not (recover and _recover_configuration_file(path, *simulated)):
            raise click.ClickException(str(exc)) from exc
    try:
        return load_configuration(path, overrides)
    except ConfigurationError as exc:
        raise click.ClickException(str(exc)) from exc


def _recover_configuration_file(path: Path | None, buttons: bool, display: bool) -> bool:
    """Replace the configuration file with one with the default values, if it is not valid.

    The file is moved to a backup next to it, and a warning is logged.
    Nothing is done if there is no file, if it cannot be read, or if it is valid
    (the error is then in the command line options), or if it cannot be replaced.
    The new file keeps the simulator for the buttons and the display, if this run uses it.

    :param path: the configuration file; if None, the default one
    :param buttons: whether this run simulates the buttons
    :param display: whether this run simulates the display
    :return: whether the file has been replaced
    """
    target = DEFAULT_CONFIGURATION_FILE_PATH.expanduser() if path is None else path
    if not target.is_file():
        return False
    try:
        load_configuration(target)
    except ConfigurationReadError:
        return False
    except ConfigurationError as exc:
        error = exc
    else:
        return False
    try:
        backup = replace_invalid_configuration_file(
            target, simulated_defaults(buttons=buttons, display=display)
        )
    except ConfigurationError as exc:
        LOGGER.error("Cannot replace the configuration file that is not valid: %s", exc)
        return False
    LOGGER.warning(
        "The configuration file '%s' is not valid (%s): moved to '%s', "
        "and replaced with the default values",
        target,
        error,
        backup,
    )
    return True


def _run_with_simulator(app: App, simulator: TkSimulator) -> None:
    """Run the application in another thread, and the simulator in this (the main) one.

    Either of them ending makes the other end too.

    :raises Exception: the error that stopped the application, if any
    """
    errors: list[Exception] = []

    def run_app() -> None:
        try:
            app.run()
        except Exception as exc:
            errors.append(exc)
        finally:
            simulator.close()

    thread = threading.Thread(target=run_app, name="mocassino-app")
    thread.start()
    try:
        simulator.run(on_window_closed=app.stop)
    finally:
        app.stop()
        thread.join()
    if errors:
        raise errors[0]


@click.command()
@click.option(
    "--brightness",
    type=click.FloatRange(0.0, 1.0),
    help="Set the brightness of the display (display.brightness), between 0.0 and 1.0.",
)
@click.option(
    "--default",
    is_flag=True,
    help="Print the default values, ignoring the configuration file and the global options "
    "(except -l / --library-directory-path and --simulator).",
)
@click.option(
    "--orientation",
    type=click.Choice([str(orientation) for orientation in ORIENTATIONS]),
    help="Set the orientation of the display (display.orientation), in degrees clockwise.",
)
@click.option(
    "-o",
    "--output-file-path",
    type=click.Path(dir_okay=False, path_type=Path),
    is_flag=False,
    flag_value=str(DEFAULT_CONFIGURATION_FILE_PATH),
    help="Write the configuration to this file instead of printing it; "
    "without a value, to the default configuration file.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Write the output file even if it already exists.",
)
@click.pass_obj
def configuration(
    options: GlobalOptions,
    brightness: float | None,
    default: bool,
    orientation: str | None,
    output_file_path: Path | None,
    yes: bool,
) -> None:
    """Print the effective configuration, in YAML format, or write it to a file."""
    effective = Configuration() if default else _load_configuration(options)
    if brightness is not None:
        effective = replace(
            effective,
            display=replace(effective.display, brightness=brightness),
        )
    if orientation is not None:
        effective = replace(
            effective,
            display=replace(effective.display, orientation=int(orientation)),
        )
    if default and options.library_directory_path is not None:
        directory_path = options.library_directory_path.expanduser()
        effective = replace(
            effective,
            library=replace(effective.library, directory_path=directory_path),
        )
    if default and options.simulator:
        effective = replace(
            effective,
            buttons=replace(effective.buttons, origin=ButtonsOrigin.SIMULATOR.value),
            display=replace(effective.display, target=DisplayTarget.SIMULATOR.value),
        )
    content = yaml.safe_dump(effective.to_dict(), sort_keys=True)
    if output_file_path is None:
        click.echo(content, nl=False)
        return
    output_file_path = output_file_path.expanduser()
    if output_file_path.exists() and not yes:
        raise click.ClickException(
            f"The file '{output_file_path}' already exists: use -y / --yes to write it anyway"
        )
    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Cannot write '{output_file_path}': {exc}") from exc
    click.echo(f"Configuration written to '{output_file_path}'")


@click.group()
@click.option(
    "--buttons-origin",
    type=click.Choice([origin.value for origin in ButtonsOrigin]),
    help="Where the button events come from (buttons.origin).",
)
@click.option(
    "-c",
    "--configuration-file-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="YAML configuration file.",
)
@click.option(
    "--display-target",
    type=click.Choice([target.value for target in DisplayTarget]),
    help="Where the screen is drawn (display.target).",
)
@click.option(
    "-l",
    "--library-directory-path",
    type=click.Path(file_okay=False, path_type=Path),
    help="Music root directory (library.directory_path).",
)
@click.option(
    "--simulator",
    is_flag=True,
    help="Shortcut for '--buttons-origin simulator --display-target simulator'.",
)
@click.option(
    "-s",
    "--state-file-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="YAML state file.",
)
@click.option("-v", "--verbose", is_flag=True, help="Log debug messages.")
@click.version_option(__version__, "-V", "--version", prog_name="mocassino")
@click.pass_context
def main(
    context: click.Context,
    buttons_origin: str | None,
    configuration_file_path: Path | None,
    display_target: str | None,
    library_directory_path: Path | None,
    simulator: bool,
    state_file_path: Path | None,
    verbose: bool,
) -> None:
    """Lightweight audio player based on MOC for Pirate Audio hats.

    The options go before the command, and are shared by all the commands.
    """
    context.obj = GlobalOptions(
        buttons_origin=buttons_origin,
        configuration_file_path=configuration_file_path,
        display_target=display_target,
        library_directory_path=library_directory_path,
        simulator=simulator,
        state_file_path=state_file_path,
    )
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


@click.command()
@click.option(
    "-b/-f",
    "--background/--foreground",
    default=None,
    help="Run detached from the terminal or attached to it (run.mode). "
    "If neither is given, as the configuration says.",
)
@click.pass_obj
def run(options: GlobalOptions, background: bool | None) -> None:
    """Run the service.

    A configuration file that is not valid is moved to a backup next to it,
    and replaced with one with the default values, so that the service can start.
    """
    effective = _load_configuration(options, recover=True)
    if background is None:
        background = effective.run.mode == RunMode.BACKGROUND
    if not effective.library.directory_path.is_dir():
        raise click.ClickException(
            f"The music root directory '{effective.library.directory_path}' does not exist"
        )
    if shutil.which(effective.system.mocp_file_path) is None:
        raise click.ClickException(f"Cannot find '{effective.system.mocp_file_path}'")
    if background:
        _daemonize()
    try:
        app = build_app(effective, options.configuration_file_path, options.state_file_path)

        def stop(signal_number: int, frame: FrameType | None) -> None:
            app.stop()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        LOGGER.info("Running, press Ctrl+C or send SIGTERM to stop")
        if app.simulator is None:
            app.run()
        else:
            _run_with_simulator(app, app.simulator)
        LOGGER.info("Stopped")
    except Exception as exc:
        LOGGER.exception("Stopped by an error")
        raise click.ClickException(f"Stopped by an error: {exc}") from exc


main.add_command(configuration)
main.add_command(run)
