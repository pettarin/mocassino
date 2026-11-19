# CLI Usage

The CLI tool `mocassino` is installed together with the package,
in the virtual environment where the package is installed.

```text
Usage: mocassino [OPTIONS] COMMAND [ARGS]...

  Lightweight audio player based on MOC for Pirate Audio hats.

  The options go before the command, and are shared by all the commands.

Options:
  --buttons-origin [gpio|none|pirateaudio|simulator]
                                  Where the button events come from
                                  (buttons.origin).
  -c, --configuration-file-path FILE
                                  YAML configuration file.
  --display-target [none|pirateaudio|simulator|st7789]
                                  Where the screen is drawn (display.target).
  -l, --library-directory-path DIRECTORY
                                  Music root directory
                                  (library.directory_path).
  -s, --simulator                 Shortcut for '--buttons-origin simulator
                                  --display-target simulator'.
  -v, --verbose                   Log debug messages.
  -V, --version                   Show the version and exit.
  --help                          Show this message and exit.

Commands:
  configuration  Print the effective configuration, in YAML format.
  run            Run the service.
```

The options above are global: they go before the command, and are shared by all the commands
(e.g., `mocassino --verbose --simulator run --foreground`).
The options of a command go after it.


## Commands

### `mocassino run`

Run the service: handle the buttons, pilot the display,
and send the playback commands to MOC.

```text
Usage: mocassino run [OPTIONS]

  Run the service.

Options:
  -b, --background / -f, --foreground
                                  Run detached from the terminal or attached
                                  to it. If neither is given, as run.mode says
                                  in the configuration.
  --help                          Show this message and exit.
```

Before starting, the command checks that the configuration is valid,
that the music root directory exists, and that `mocp` can be found:
if not, it prints the error and exits.

When it starts, the service starts the MOC server, if it is not already running,
and sets the MOC volume to the one saved in the state file or, if there is none,
to `playback.volume_default`.

> [!NOTE]
> MOC does not report its volume to command line clients,
> so `mocassino` keeps track of the volume by itself,
> and saves it in its state file.

#### Background And Foreground

With `-b / --background`, the command prints the identifier of the process running the service, and returns:

```bash
$ mocassino run
mocassino is running in background (PID 15875)
```

The service keeps running, detached from the terminal.
Its log messages are sent to the system log, if available:

```bash
$ journalctl -t mocassino
```

To stop the service, send it the `SIGTERM` signal:

```bash
$ kill 15875
```

With `-f / --foreground`, the service stays attached to the terminal,
where it writes its log messages, until `Ctrl+C` is pressed.

When neither option is given, the `run.mode` setting of the configuration file decides.
It is `background` by default; on a PC, where the simulator is typically used,
it can be set to always run in foreground:

```yaml
run:
  mode: foreground
```

#### Running Without The Hardware

The buttons and the display can be replaced independently, with the global options:

| Option | Value | Meaning |
|---|---|---|
| `--buttons-origin` | `pirateaudio` | The buttons of the Pirate Audio hat (default) |
| `--buttons-origin` | `gpio` | Synonym of `pirateaudio` |
| `--buttons-origin` | `simulator` | The buttons of the simulator window |
| `--buttons-origin` | `none` | No buttons |
| `--display-target` | `pirateaudio` | The display of the Pirate Audio hat (default) |
| `--display-target` | `st7789` | Synonym of `pirateaudio` |
| `--display-target` | `simulator` | The simulator window |
| `--display-target` | `none` | No display: no draw action is performed |

The `-s / --simulator` option selects the simulator for both.
The simulator is a window showing the display, enlarged, and the four buttons:

```bash
$ mocassino --simulator --library-directory-path ~/music run --foreground
```

In the simulator window:

- click a button for a short press,
  or keep it pressed for a long press and for the hold presses, which repeat until it is released;
- alternatively, type `a`, `b`, `x`, or `y` for a short press,
  and `A`, `B`, `X`, or `Y` for a long press together with a single hold press;
- or use the arrow keys: left for `A`, right for `B`, up for `X`, and down for `Y`,
  for a short press; with `Shift`, for a long press together with a single hold press;
- close the window to stop the service.

With the simulator, `Shut down now` in the `System` menu never runs `system.shutdown_command`,
so that the development machine is not shut down by mistake:
the command is only logged, and the window goes dark as the display would,
until the window is closed.

The simulator requires Tk (the `tkinter` module of the Python standard library),
which is only loaded when the simulator is used.


### `mocassino configuration`

Print the effective configuration, in YAML format,
that is, the default values changed by the configuration file
and by the command line options.
The command uses the same global options of `mocassino run`,
so it can be used to check what the service would run with
(e.g., `mocassino --simulator configuration`).

```text
Usage: mocassino configuration [OPTIONS]

  Print the effective configuration, in YAML format.

Options:
  --brightness FLOAT RANGE      Set the brightness of the display
                                (display.brightness), between 0.0 and 1.0.
                                [0.0<=x<=1.0]
  --default                     Print the default values, ignoring the
                                configuration file and the global options.
  --orientation [0|90|180|270]  Set the orientation of the display
                                (display.orientation), in degrees clockwise.
  -o, --output-file-path FILE   Write the configuration to this file instead
                                of printing it; without a value, to the
                                default configuration file.
  -y, --yes                     Write the output file even if it already
                                exists.
  --help                        Show this message and exit.
```

With `-o / --output-file-path`, the configuration is written to a file instead of being printed.
The value is optional: without it, the file is the default configuration file,
`~/.config/mocassino/configuration.yaml`.
If the file already exists, the command fails without touching it,
unless `-y / --yes` is given too:

```bash
$ # write the effective configuration, with the simulator selected, to a file
$ mocassino --simulator configuration -o /path/to/configuration.yaml
Configuration written to '/path/to/configuration.yaml'

$ # write the default values to the default configuration file, replacing it
$ mocassino configuration --default -o -y
```

With `--orientation`, the configuration printed or written has that `display.orientation`,
whatever the configuration file says; it also applies with `--default`.
Together with `-o`, it sets the orientation of the display for the next runs:

```bash
$ # turn what is shown on the display upside down, keeping the rest of the configuration
$ mocassino configuration --orientation 180 -o -y
```

Likewise, with `--brightness`, the configuration printed or written has that `display.brightness`,
a value between `0.0` and `1.0`, whatever the configuration file says;
it also applies with `--default`, and it can be given together with `--orientation`:

```bash
$ # dim the display to 60% for the next runs, keeping the rest of the configuration
$ mocassino configuration --brightness 0.6 -o -y
```

With `--default`, it prints the default values instead,
whatever the configuration file and the global options say.
It works even if the configuration file is not valid,
and its output can be used as a starting point for a configuration file:

```bash
$ mocassino configuration --default
buttons:
  button_map:
    menu:
      A: menu_back
      B: menu_select
      X: menu_up
      X_long: menu_select
      Y: menu_down
      Y_long: menu_select
    playback:
      A: play_pause
      A_long: open_menu
      B: next
      B_long: previous
      X: volume_up
      X_hold: seek_forward
      Y: volume_down
      Y_hold: seek_backward
  long_press_time: 0.6
  origin: pirateaudio
  repeat_hold_time: 0.3
display:
  brightness: 1.0
  font_file_path: null
  orientation: 0
  show_progress_bar: true
  show_side_icons: true
  show_volume_bar: true
  target: pirateaudio
  tick: 0.5
library:
  directory_path: /music
playback:
  seek_step: 10
  volume_default: 50
  volume_step: 5
run:
  mode: background
startup:
  playlist: use_saved
  state: use_saved
  volume: use_saved
system:
  moc_state_on_exit: do_nothing
  mocp_file_path: mocp
  shutdown_command:
  - sudo
  - shutdown
  - -h
  - now
```


## Configuration File

The permanent settings are read from a YAML file:
the one given with `-c / --configuration-file-path`, or,
if the option is not given and the file exists,
`~/.config/mocassino/configuration.yaml`.

The file has the same structure printed by `mocassino configuration`.
Every section and every key is optional:
what is missing takes its default value.
Unknown sections, unknown keys, and invalid values are reported as errors.

| Key | Default | Meaning |
|---|---|---|
| `buttons.button_map` | see below | The action of each button, in each mode |
| `buttons.long_press_time` | `0.6` | How long a button must be held for a long press, in seconds |
| `buttons.origin` | `pirateaudio` | Where the button events come from: `pirateaudio` (or its synonym `gpio`), `none`, or `simulator` |
| `buttons.repeat_hold_time` | `0.3` | How often the hold press of a held button repeats, in seconds |
| `display.font_file_path` | none | The TrueType font; if not set, the font built in Pillow |
| `display.brightness` | `1.0` | The brightness of the display, between `0.0` (backlight off) and `1.0` (full brightness); it only applies to the Pirate Audio display, not to the simulator; it can be changed from the `Settings` menu |
| `display.orientation` | `0` | By how many degrees, clockwise, what is shown on the display is rotated: `0`, `90`, `180`, or `270`; it can be changed from the `Settings` menu |
| `display.show_progress_bar` | `true` | Whether the progress bar of the track is shown in playback mode; it can be changed from the `Settings` menu |
| `display.show_side_icons` | `true` | Whether the icons of the buttons are shown in playback mode; it can be changed from the `Settings` menu |
| `display.show_volume_bar` | `true` | Whether the volume bar is shown in playback mode; it can be changed from the `Settings` menu |
| `display.target` | `pirateaudio` | Where the screen is drawn: `pirateaudio` (or its synonym `st7789`), `none`, or `simulator` |
| `display.tick` | `0.5` | How often the MOC status is read and the screen updated, in seconds |
| `library.directory_path` | `/music` | The music root directory |
| `playback.seek_step` | `10` | The amount of each seek, in seconds; it can be changed from the `Settings` menu |
| `playback.volume_default` | `50` | The default volume, between 0 and 100: the one set when the service starts if `startup.volume` is `use_default`, or if there is no saved volume; it can be changed from the `Settings` menu |
| `playback.volume_step` | `5` | The amount of each volume change, between 1 and 100; it can be changed from the `Settings` menu |
| `run.mode` | `background` | Whether the service runs in `background` or in `foreground` when neither `-b` nor `-f` is given |
| `startup.playlist` | `use_saved` | What the service does about the playlist when it starts: `open_library`, `use_moc_state`, or `use_saved` (see below); it can be changed from the `Settings` menu |
| `startup.state` | `use_saved` | What playback state the service sets when it starts: `pause`, `play`, `stop`, or `use_saved` (see below); it can be changed from the `Settings` menu |
| `startup.volume` | `use_saved` | What volume the service sets when it starts: `use_default` (the one in `playback.volume_default`) or `use_saved` (the one saved in the state file); it can be changed from the `Settings` menu |
| `system.moc_state_on_exit` | `do_nothing` | What the service does to MOC when it exits (e.g., when it is stopped, or when the host shuts down): `do_nothing`, `pause`, `stop`, or `quit` (which shuts the MOC server down); the state is saved before, so that the playback can be resumed on the next start; it can be changed from the `System` menu |
| `system.mocp_file_path` | `mocp` | The `mocp` executable |
| `system.shutdown_command` | `sudo shutdown -h now` | The command shutting down the host, as a string or as a list; it is never run when the simulator is used |

> [!NOTE]
> The font built in Pillow only has the basic Latin letters:
> accented letters are drawn as empty boxes.
> Set `display.font_file_path` to a font with the characters of your music library,
> e.g., `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`.

The command line options take precedence over the configuration file:

| Option | Key |
|---|---|
| `--buttons-origin` | `buttons.origin` |
| `--display-target` | `display.target` |
| `-l / --library-directory-path` | `library.directory_path` |

> [!NOTE]
> A setting changed from the `Settings` menu is saved in the configuration file in use:
> the one given with `-c / --configuration-file-path`, or the default one,
> which is created if it does not exist.
> The other values of the file are kept, but the file is written again as a whole:
> the comments in it are lost.

An example of configuration file:

```yaml
display:
  font_file_path: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
library:
  directory_path: /home/pi/music
playback:
  volume_default: 30
```

### State File

The player remembers its state from one run to the next
in the `~/.config/mocassino/state.yaml` file, which it writes by itself:

```yaml
playback:
  directory_path: /music/Artist/Album
  file_path: /music/Artist/Album/003_Track.flac
  seek: 95
  state: playing
  volume: 85
```

| Key | Meaning |
|---|---|
| `playback.directory_path` | What was being played from: the directory selected in the `Library` menu or, if a single file was selected, that file; when that is not known (e.g., the playback was not started from the `Library` menu), the directory of the track |
| `playback.file_path` | The track that was playing |
| `playback.seek` | The position in the track, in seconds |
| `playback.state` | `playing`, `paused`, or `stopped` |
| `playback.volume` | The volume, between 0 and 100 |

When nothing is playing, the directory and the file are `null`, the position is `0`,
and the state is `stopped`.

The state is saved when the track changes, when the volume changes,
when a setting is changed from the menus, and when the service is stopped.
Shutting down the host from the `System` menu saves it too, before the shutdown is asked.
The file is only written when its content would change.

When the service starts:

- it restores the volume from the state file, if it has one
  and `startup.volume` is `use_saved`;
  otherwise, it applies `playback.volume_default` from the configuration file;
- it sets up the playlist as `startup.playlist` says:

  | Value | What happens |
  |---|---|
  | `open_library` | MOC is stopped, and the `Library` menu is shown, to select what to play |
  | `use_moc_state` | MOC is left as it is: the display shows whatever it is playing |
  | `use_saved` | MOC is stopped, and the playback saved in the state file is resumed |

- it sets the playback state as `startup.state` says,
  unless `startup.playlist` is `open_library`, in which case it has no effect:

  | Value | With `startup.playlist: use_saved` | With `startup.playlist: use_moc_state` |
  |---|---|---|
  | `pause` | The saved track is resumed at the saved position, paused | MOC is paused, if it is playing |
  | `play` | The saved track is resumed at the saved position, playing | MOC is made to play: resumed if paused, started from the first track of its playlist if stopped |
  | `stop` | The saved directory is given to MOC as its playlist, but nothing is played: play/pause then starts it from its first track | MOC is stopped |
  | `use_saved` | The saved track is resumed at the saved position, playing or paused as it was saved | MOC is left as it is |

To resume the saved playback, the service plays the saved directory from its first track
with the volume at zero, skips to the saved track, goes to the saved position,
pauses if the playback has to be paused, and only then sets the volume.
If the state file has the track but not the directory, the directory of the track is played.
If the saved playback cannot be resumed (e.g., the file no longer exists),
it plays nothing, and blanks the directory, the file, and the position in the state file.

> [!NOTE]
> Once the state file has a volume, `playback.volume_default` is no longer used,
> unless `startup.volume` is set to `use_default`.

> [!NOTE]
> The position is saved at the moments listed above, not continuously:
> if the device loses power while playing, the track is resumed from where it was
> when the state was last saved, which is usually its start.


### Button Map

The four buttons of the Pirate Audio hat are
`A` (top-left), `B` (bottom-left), `X` (top-right), and `Y` (bottom-right).
Each of them can be pressed shortly or held, which gives three kinds of press:

| Press | Key in the button map | When it happens |
|---|---|---|
| Short | `A` | When the button is released before `buttons.long_press_time` |
| Long | `A_long` | Once, as soon as the button has been held for `buttons.long_press_time` |
| Hold | `A_hold` | Together with the long press, and then again every `buttons.repeat_hold_time`, until the button is released |

Use the long press for the actions that must happen once (e.g., opening the menu),
and the hold press for those that must go on while the button is held (e.g., seeking).

The default button map is:

| Button | Playback mode | Menu mode |
|---|---|---|
| `A` | `play_pause` | `menu_back` |
| `A_long` | `open_menu` | |
| `B` | `next` | `menu_select` |
| `B_long` | `previous` | |
| `X` | `volume_up` | `menu_up` |
| `X_hold` | `seek_forward` | |
| `X_long` | | `menu_select` |
| `Y` | `volume_down` | `menu_down` |
| `Y_hold` | `seek_backward` | |
| `Y_long` | | `menu_select` |

The actions are:

| Action | Meaning |
|---|---|
| `menu_back` | Go back one level; from the top level menu, go back to the playback |
| `menu_down` | Select the next item of the menu |
| `menu_select` | Open the selected item, or perform its command |
| `menu_up` | Select the previous item of the menu |
| `next` | Play the next track |
| `open_menu` | Show the top level menu |
| `play_pause` | Toggle between playing and paused; if stopped, play the playlist |
| `previous` | Play the previous track |
| `seek_backward` | Seek backward in the current track, by `playback.seek_step` seconds |
| `seek_forward` | Seek forward in the current track, by `playback.seek_step` seconds |
| `volume_down` | Turn the volume down |
| `volume_up` | Turn the volume up |

In the configuration file, list only what differs from the default;
set an action to `null` to leave a button without action:

```yaml
buttons:
  button_map:
    playback:
      B: previous
      B_long: null
      X_long: next
```

With the default values, holding `X` in playback mode seeks 10 seconds forward
after 0.6 seconds, and then 10 more seconds every 0.3 seconds, until `X` is released.

### Button Icons

In playback mode, a band of 20 pixels on each side of the screen
shows the icons of the actions of the buttons:
those of `A` and `X` at the top, and those of `B` and `Y` at the bottom.
Each button has two icons: at the very top or bottom,
the icon of its long press or, if it has none, of its hold press;
next to it, towards the middle of the screen, the icon of its short press.

The icons follow the button map: a button without action,
or with an action that has no icon (the `menu_*` actions), shows no icon.

The volume is shown as a vertical bar in the band on the right, between the icons of `X` and `Y`:
with the default button map, between the icon turning the volume up, where the bar is full,
and the icon turning the volume down, where the bar is empty.

Set `display.show_side_icons` to `false` to hide the icons,
and `display.show_volume_bar` to `false` to hide the volume bar.
The band on the left is reserved to the icons, and the band on the right
to the icons and the volume bar: a band that has nothing to show
is used by the playback information.
Set `display.show_progress_bar` to `false` to hide the progress bar:
the times and the state of the playback are still shown below its place.
The three can also be shown or hidden while the service runs, from the `Settings` menu.


### Orientation

With `display.orientation`, what is shown on the display is rotated clockwise by
90, 180, or 270 degrees, for a device that is mounted or held turned
the other way by the same angle.

The buttons follow the rotation: for who looks at the display the right way up,
the button at each corner keeps doing the same thing.
For example, with `180` the device is used upside down, and its `Y` button,
which is then at the top-left, does what `A` does at `0`.
In the button map, the names of the buttons are then those of the corners
(`A` top-left, `B` bottom-left, `X` top-right, `Y` bottom-right), not those printed on the hat.

| Orientation | `A` does what is mapped to | `B` | `X` | `Y` |
|---|---|---|---|---|
| `0` | `A` | `B` | `X` | `Y` |
| `90` | `B` | `Y` | `A` | `X` |
| `180` | `Y` | `X` | `B` | `A` |
| `270` | `X` | `A` | `Y` | `B` |

With `90` and `270` the buttons of the hat end up above and below the display,
not at its sides: the icons of the buttons are still drawn in the bands at the sides,
near the corner of each button.


## Menus

The top level menu has the following items:

- `Library`: browse the music root directory.
  Each directory lists `Play this folder`, its subdirectories,
  and its audio files (FLAC, MP3, OGG, and WAV).
  Selecting `Play this folder` or an audio file
  replaces the MOC playlist with it, and plays it.
- `Settings`: change the settings of the running service.
  A setting that is either on or off has a square on the right of its row:
  solid when it is on, empty when it is off. Selecting the item changes it.
  The new value is also saved in the configuration file,
  so that it is kept when the service is started again.
  - `Display`: the settings of the display.
    - `Brightness (%)` (`display.brightness`): a menu with the brightnesses from `0` to `100`,
      in steps of 5; the current one has the solid square.
      The change is immediate; it is saved as a value between `0.0` and `1.0`.
      At `0` the backlight is off, and the display is dark:
      the brightness can be raised again from the same menu, without seeing it,
      or by editing the configuration file.
    - `Orientation` (`display.orientation`): a menu with the four choices
      `0`, `90`, `180`, and `270`; the current one has the solid square.
      The change is immediate (see below).
    - `Show progress bar` (`display.show_progress_bar`):
      whether the progress bar of the track is shown in playback mode.
    - `Show side icons` (`display.show_side_icons`):
      whether the icons of the buttons are shown in playback mode.
    - `Show volume bar` (`display.show_volume_bar`):
      whether the volume bar is shown in playback mode.
  - `Playback`: the amount of each seek, the default volume, and the amount of each volume change.
    The steps take effect immediately;
    the default volume, the next time the service starts and uses it.
    - `Seek step (s)` (`playback.seek_step`): a menu with the choices
      `1`, `2`, `5`, `10`, `30`, and `60` seconds.
    - `Volume default (%)` (`playback.volume_default`): a menu with the volumes from `0` to `100`,
      in steps of 5; the current one has the solid square.
    - `Volume step (%)` (`playback.volume_step`): a menu with the choices
      `1`, `2`, `4`, `5`, and `10`.
  - `Startup`: the settings of what the service does when it starts.
    They take effect the next time the service starts.
    - `Playlist` (`startup.playlist`): a menu with the three choices
      `Open library`, `Use MOC state`, and `Use saved`; the current one has the solid square.
    - `State` (`startup.state`): a menu with the four choices
      `Pause`, `Play`, `Stop`, and `Use saved`; the current one has the solid square.
    - `Volume` (`startup.volume`): a menu with the two choices
      `Use default` and `Use saved`; the current one has the solid square.
- `System`: show the name and the IP address of the host,
  `MOC state on exit`, `Reset settings`, and `Shut down`.
  `MOC state on exit` (`system.moc_state_on_exit`) is a menu with the four choices
  `Do nothing`, `Pause`, `Quit`, and `Stop`; the current one has the solid square.
  The choice applies when the service exits, after its state has been saved.
  `Reset settings` asks for confirmation, then replaces the configuration file
  with one holding all the default values, as `mocassino configuration --default` prints them;
  the defaults of the settings take effect at once, the other values the next time
  the service starts.
  All the values are reset, not only those of the `Settings` menu
  (e.g., `library.directory_path` and `system.shutdown_command` too),
  except that the simulator is kept for the buttons and for the display, if it is in use.
  `Shut down` asks for confirmation
  before running `system.shutdown_command`.
  The display is turned off before the command is run,
  and turned on again if the command fails.
  With the simulator, the command is only logged, and never run.

To leave the top level menu and go back to the playback, press the back button
(`A`, with the default button map).
