# Changelog

All notable changes to this project will be documented in this file.

> [!NOTE]
> The format is based on
> [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
> and this project adheres to
> [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.3] - To be released

### Added

- The `display.ui_elements.show_timers` setting, and the `Show timers` item
  of the `UI elements` menu, to hide the times and the icon of the state of the playback
- The `display.ui_elements.right_timer_value` setting, and the `Right timer value` menu
  in the `UI elements` menu, to have the timer on the right show the time remaining
  (`remaining_time`) instead of the end time, the length of the track (`end_time`)
- The `save_state` section (`on_exit`, `on_playback_tick`, `on_startup`, `on_state_change`,
  `on_track_change`, `on_volume_change`), and the `Save state` menu in the `Settings` menu,
  to choose when the state file is written

### Changed

- The state file is no longer written when a setting is changed from the menus
- `mocassino configuration --default` honors the global options
  `-l / --library-directory-path` and `-s / --simulator`
- In playback mode, without the progress bar, the album moves down to its place,
  right above the times
- The default music root directory (`library.directory_path`) is the home directory
  of the user running the service, instead of `/music`
- The default values of the configuration are defined in the new `mocassino.defaults` module
- The choices of the settings (e.g., `buttons.origin`), the volume limits,
  the modes of the application, the actions, the buttons,
  and the kinds of button press (`Press`, renamed `ButtonPress`)
  are defined in the new `mocassino.constants` module


## [0.0.2] - 2026-11-20

### Added

- First actual implementation of the service

## [0.0.1] - 2026-11-18

### Added

- Initial release (just to reserve the package name in PyPI)
