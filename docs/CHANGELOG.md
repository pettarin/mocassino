# Changelog

All notable changes to this project will be documented in this file.

> [!NOTE]
> The format is based on
> [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
> and this project adheres to
> [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.7] - To be released

### Added

- The `version` command

### Changed

- Renamed the `--brightness` and `--orientation` options
  of the `configuration` command as the global options
  `--display-brightness` and `--display-orientation`


## [0.0.6] - 2026-11-27

### Added

- The `Library directory` item in the `Settings > Run` menu
- The `Restart service` item in the `System` menu

### Changed

- Reboot command in the example configuration file and in the documentation


## [0.0.5] - 2026-11-27

### Added

- The `install.sh` script

### Changed

- Default reboot command to `sudo systemctl reboot`


## [0.0.4] - 2026-11-21

### Added

- Global option `-s / --state-file-path` to set the path of the state file

### Removed

- The short form `-s` for the global option `--simulator`


## [0.0.3] - 2026-11-20

### Added

- Some additional improvements to the usuability of the service,
  not worth mentioning explicitly one by one


## [0.0.2] - 2026-11-20

### Added

- First actual implementation of the service


## [0.0.1] - 2026-11-18

### Added

- Initial release (just to reserve the package name in PyPI)
