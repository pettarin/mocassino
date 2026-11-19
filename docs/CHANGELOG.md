# Changelog

All notable changes to this project will be documented in this file.

> [!NOTE]
> The format is based on
> [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
> and this project adheres to
> [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.2] - To Be Released

### Added

- First actual implementation of the service
- A Tk-based simulator that can be used on a PC (with MOC installed)
- Support for the Pirate Audio boards made before 23 January 2020, whose `Y` button is on pin 20:
  `Y` is read on both pins 24 and 20, whichever can be claimed
- The `display.ui_elements` configuration keys, and the `UI elements` menu of the display settings,
  to show or hide the side icons and the progress, playlist, and volume bars
  (development versions used `display.show_side_icons` etc.: a configuration file written by them
  has to be updated, or it is backed up and replaced with the default values)
- The `display.brightness` configuration key, the `Brightness (%)` menu of the display settings,
  and the `--brightness` option of the `configuration` command, to set the brightness of the display

## [0.0.1] - 2026-11-18

### Added

- Initial release (just to reserve the package name in PyPI)
