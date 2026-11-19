"""Tests for the command line interface.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
import signal
import threading

import pytest
import yaml
from click.testing import CliRunner

import mocassino
from mocassino.app import App
from mocassino.cli import _daemonize, _run_with_simulator, main
from mocassino.configuration import Configuration
from mocassino.model.moc import MocError
from mocassino.simulator.tk import TkSimulator

NULL_DESCRIPTOR = 9999


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point the home directory to a temporary one, so the user's files are never read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def runner():
    return CliRunner()


class TestConfigurationCommand:
    """Tests for the configuration command"""

    def test_configuration_file(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("playback:\n  initial_volume: 30\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "--configuration-file-path", str(path)])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output)["playback"]["initial_volume"] == 30

    def test_configuration_file_invalid(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("zoom: 2\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "--configuration-file-path", str(path)])
        assert result.exit_code == 1
        assert "Error: Unknown configuration keys: zoom" in result.output

    def test_defaults(self, runner):
        result = runner.invoke(main, ["configuration"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_overrides(self, runner):
        result = runner.invoke(
            main,
            [
                "configuration",
                "--buttons-origin",
                "none",
                "--display-target",
                "none",
                "--library-directory-path",
                "/srv/music",
            ],
        )
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "none"
        assert output["display"]["target"] == "none"
        assert output["library"]["directory_path"] == "/srv/music"

    def test_simulator(self, runner):
        result = runner.invoke(main, ["configuration", "--simulator"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "simulator"

    def test_simulator_does_not_override_explicit_options(self, runner):
        result = runner.invoke(main, ["configuration", "--simulator", "--display-target", "none"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "none"


class TestDaemonize:
    """Tests for the _daemonize function"""

    @pytest.fixture
    def root_handlers(self):
        """Restore the handlers of the root logger after the test."""
        root = logging.getLogger()
        handlers = list(root.handlers)
        yield
        root.handlers = handlers

    @pytest.fixture
    def system(self, mocker):
        """Replace the system calls, so that the tests never fork nor lose their output.

        Only the calls about the null device go to the replacements:
        the others (e.g., those of pytest itself) go to the real functions.
        """
        real_close, real_dup2, real_open = os.close, os.dup2, os.open
        system = mocker.Mock()
        system.fork = mocker.patch("mocassino.cli.os.fork", return_value=0)
        system.setsid = mocker.patch("mocassino.cli.os.setsid")
        system.closerange = mocker.patch("mocassino.cli.os.closerange")

        def fake_close(descriptor):
            if descriptor != NULL_DESCRIPTOR:
                return real_close(descriptor)
            return system.close(descriptor)

        def fake_dup2(descriptor, target, *args, **kwargs):
            if descriptor != NULL_DESCRIPTOR:
                return real_dup2(descriptor, target, *args, **kwargs)
            return system.dup2(descriptor, target)

        def fake_open(path, *args, **kwargs):
            if path != os.devnull:
                return real_open(path, *args, **kwargs)
            system.open(path, *args, **kwargs)
            return NULL_DESCRIPTOR

        mocker.patch("mocassino.cli.os.close", side_effect=fake_close)
        mocker.patch("mocassino.cli.os.dup2", side_effect=fake_dup2)
        mocker.patch("mocassino.cli.os.open", side_effect=fake_open)
        return system

    def test_background_process(self, mocker, system, root_handlers, tmp_path):
        socket_path = tmp_path / "log"
        socket_path.touch()
        mocker.patch("mocassino.cli.SYSLOG_SOCKET_PATH", socket_path)
        handler_class = mocker.patch("mocassino.cli.SysLogHandler")
        _daemonize()
        system.setsid.assert_called_once_with()
        system.open.assert_called_once_with(os.devnull, os.O_RDWR)
        descriptors = [call.args for call in system.dup2.call_args_list]
        assert descriptors == [(NULL_DESCRIPTOR, 0), (NULL_DESCRIPTOR, 1), (NULL_DESCRIPTOR, 2)]
        system.close.assert_called_once_with(NULL_DESCRIPTOR)
        system.closerange.assert_called_once_with(3, os.sysconf("SC_OPEN_MAX"))
        handler_class.assert_called_once_with(address=str(socket_path))
        assert logging.getLogger().handlers == [handler_class.return_value]

    def test_background_process_without_system_log(self, mocker, system, root_handlers, tmp_path):
        mocker.patch("mocassino.cli.SYSLOG_SOCKET_PATH", tmp_path / "missing")
        _daemonize()
        assert logging.getLogger().handlers == []

    def test_foreground_process(self, system, capsys):
        system.fork.return_value = 4242
        with pytest.raises(SystemExit) as info:
            _daemonize()
        assert info.value.code == 0
        assert capsys.readouterr().out == "mocassino is running in background (PID 4242)\n"
        system.setsid.assert_not_called()
        system.dup2.assert_not_called()
        system.closerange.assert_not_called()


class TestRunWithSimulator:
    """Tests for the _run_with_simulator function"""

    @pytest.fixture
    def app(self, mocker):
        return mocker.create_autospec(App, instance=True)

    @pytest.fixture
    def simulator(self, mocker):
        return mocker.create_autospec(TkSimulator, instance=True)

    def test_application_error(self, app, simulator):
        app.run.side_effect = MocError("Server exited!")
        with pytest.raises(MocError, match="Server exited!"):
            _run_with_simulator(app, simulator)
        simulator.close.assert_called_once_with()

    def test_both_are_run(self, app, simulator):
        threads = []
        app.run.side_effect = lambda: threads.append(threading.current_thread())
        simulator.run.side_effect = lambda **kwargs: threads.append(threading.current_thread())
        _run_with_simulator(app, simulator)
        assert len(threads) == 2
        assert threading.main_thread() in threads
        assert threads[0] is not threads[1]
        simulator.run.assert_called_once_with(on_window_closed=app.stop)
        simulator.close.assert_called_once_with()
        app.stop.assert_called_once_with()

    def test_simulator_error(self, app, simulator):
        simulator.run.side_effect = RuntimeError("no display name")
        with pytest.raises(RuntimeError, match="no display name"):
            _run_with_simulator(app, simulator)
        app.stop.assert_called_once_with()
        app.run.assert_called_once_with()


class TestMain:
    """Tests for the main group"""

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output

    def test_verbose(self, runner):
        result = runner.invoke(main, ["--verbose", "configuration"])
        assert result.exit_code == 0

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert result.output == f"mocassino, version {mocassino.__version__}\n"


class TestRunCommand:
    """Tests for the run command"""

    @pytest.fixture
    def app(self, mocker):
        """Replace the application, so that nothing is really run."""
        app = mocker.patch("mocassino.cli.build_app").return_value
        app.simulator = None
        return app

    @pytest.fixture
    def arguments(self, tmp_path):
        """The arguments running the service on an existing directory with an existing mocp."""
        return ["run", "--library-directory-path", str(tmp_path), "--display-target", "none"]

    @pytest.fixture
    def daemonize(self, mocker):
        return mocker.patch("mocassino.cli._daemonize")

    @pytest.fixture(autouse=True)
    def set_signal(self, mocker):
        """Replace signal.signal, so that the handlers of the tests are left alone."""
        return mocker.patch("mocassino.cli.signal.signal")

    @pytest.fixture(autouse=True)
    def which(self, mocker):
        return mocker.patch("mocassino.cli.shutil.which", return_value="/usr/bin/mocp")

    def test_background(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, [*arguments, "--background"])
        assert result.exit_code == 0
        daemonize.assert_called_once_with()
        app.run.assert_called_once_with()

    def test_background_is_the_default(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        daemonize.assert_called_once_with()
        app.run.assert_called_once_with()

    def test_configuration_is_used(self, runner, mocker, arguments, daemonize, tmp_path):
        build_app = mocker.patch("mocassino.cli.build_app")
        build_app.return_value.simulator = None
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        effective = build_app.call_args.args[0]
        assert effective.display.target == "none"
        assert effective.library.directory_path == tmp_path

    def test_error_while_building(self, runner, mocker, arguments, daemonize):
        mocker.patch("mocassino.cli.build_app", side_effect=OSError("cannot open resource"))
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Stopped by an error: cannot open resource" in result.output

    def test_error_while_running(self, runner, app, arguments, daemonize):
        app.run.side_effect = MocError("Server exited!")
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Stopped by an error: Server exited!" in result.output

    def test_foreground(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, [*arguments, "--foreground"])
        assert result.exit_code == 0
        daemonize.assert_not_called()
        app.run.assert_called_once_with()

    def test_invalid_configuration(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, [*arguments, "--configuration-file-path", "missing.yaml"])
        assert result.exit_code == 1
        assert "Error: Cannot read configuration file" in result.output
        daemonize.assert_not_called()

    def test_mocp_not_found(self, runner, app, arguments, daemonize, which):
        which.return_value = None
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Cannot find 'mocp'" in result.output
        daemonize.assert_not_called()
        app.run.assert_not_called()

    def test_music_root_directory_missing(self, runner, app, daemonize, tmp_path):
        missing = tmp_path / "missing"
        result = runner.invoke(main, ["run", "--library-directory-path", str(missing)])
        assert result.exit_code == 1
        assert f"Error: The music root directory '{missing}' does not exist" in result.output
        daemonize.assert_not_called()
        app.run.assert_not_called()

    def test_simulator(self, runner, mocker, app, arguments, daemonize):
        run_with_simulator = mocker.patch("mocassino.cli._run_with_simulator")
        app.simulator = mocker.sentinel.simulator
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        run_with_simulator.assert_called_once_with(app, mocker.sentinel.simulator)
        app.run.assert_not_called()

    def test_signals_stop_the_application(self, runner, app, arguments, daemonize, set_signal):
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        handlers = {call.args[0]: call.args[1] for call in set_signal.call_args_list}
        assert set(handlers) == {signal.SIGINT, signal.SIGTERM}
        app.stop.assert_not_called()
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        app.stop.assert_called_once_with()
