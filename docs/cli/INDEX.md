# CLI Usage

The CLI tool `mocassino` is installed together with the package,
in the virtual environment where the package is installed.

```text
Usage: mocassino [OPTIONS] COMMAND [ARGS]...

  Lightweight audio player based on MOC for Pirate Audio hats.

Options:
  -v, --verbose  Log debug messages.
  --version      Show the version and exit.
  --help         Show this message and exit.

Commands:
  configuration  Print the effective configuration, in YAML format.
  run            Run the service.
```

The `-v / --verbose` option goes before the command
(e.g., `mocassino --verbose run --foreground`).


## Commands

### `mocassino run`

Run the service: handle the buttons, pilot the display,
and send the playback commands to MOC.

```text
Usage: mocassino run [OPTIONS]

  Run the service.

Options:
  --background / --foreground     Run detached from the terminal (default) or
                                  attached to it.
  --buttons-origin [gpio|none|simulator]
                                  Where the button events come from
                                  (buttons.origin).
  --configuration-file-path FILE  YAML configuration file.
  --display-target [none|simulator|st7789]
                                  Where the screen is drawn (display.target).
  --library-directory-path DIRECTORY
                                  Music root directory
                                  (library.directory_path).
  --simulator                     Shortcut for '--buttons-origin simulator
                                  --display-target simulator'.
  --help                          Show this message and exit.
```

Before starting, the command checks that the configuration is valid,
that the music root directory exists, and that `mocp` can be found:
if not, it prints the error and exits.

When it starts, the service starts the MOC server, if it is not already running,
and sets the MOC volume to `playback.initial_volume`.

> [!NOTE]
> MOC does not report its volume to command line clients,
> so `mocassino` keeps track of the volume by itself,
> starting from `playback.initial_volume`.

#### Background And Foreground

With `--background`, which is the default,
the command prints the identifier of the process running the service, and returns:

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

With `--foreground`, the service stays attached to the terminal,
where it writes its log messages, until `Ctrl+C` is pressed.

#### Running Without The Hardware

The buttons and the display can be replaced independently:

| Option | Value | Meaning |
|---|---|---|
| `--buttons-origin` | `gpio` | The buttons of the Pirate Audio hat (default) |
| `--buttons-origin` | `simulator` | The buttons of the simulator window |
| `--buttons-origin` | `none` | No buttons |
| `--display-target` | `st7789` | The display of the Pirate Audio hat (default) |
| `--display-target` | `simulator` | The simulator window |
| `--display-target` | `none` | No display: no draw action is performed |

The `--simulator` option selects the simulator for both.
The simulator is a window showing the display, enlarged, and the four buttons:

```bash
$ mocassino run --foreground --simulator --library-directory-path ~/music
```

In the simulator window:

- click a button for a short press,
  or keep it pressed for a long press and for the hold presses, which repeat until it is released;
- alternatively, type `a`, `b`, `x`, or `y` for a short press,
  and `A`, `B`, `X`, or `Y` for a long press together with a single hold press;
- close the window to stop the service.

The simulator requires Tk (the `tkinter` module of the Python standard library),
which is only loaded when the simulator is used.


### `mocassino configuration`

Print the effective configuration, in YAML format,
that is, the default values changed by the configuration file
and by the command line options.
The command accepts the same configuration options of `mocassino run`,
so it can be used to check what the service would run with.

```text
Usage: mocassino configuration [OPTIONS]

  Print the effective configuration, in YAML format.

Options:
  --buttons-origin [gpio|none|simulator]
                                  Where the button events come from
                                  (buttons.origin).
  --configuration-file-path FILE  YAML configuration file.
  --display-target [none|simulator|st7789]
                                  Where the screen is drawn (display.target).
  --library-directory-path DIRECTORY
                                  Music root directory
                                  (library.directory_path).
  --simulator                     Shortcut for '--buttons-origin simulator
                                  --display-target simulator'.
  --help                          Show this message and exit.
```

Without options and without a configuration file, it prints the default values:

```bash
$ mocassino configuration
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
      B_hold: previous
      X: volume_up
      X_hold: seek_forward
      Y: volume_down
      Y_hold: seek_backward
  long_press_time: 0.6
  origin: gpio
  repeat_hold_time: 0.3
display:
  font_file_path: null
  show_side_icons: true
  target: st7789
  tick: 0.5
library:
  directory_path: /music
playback:
  initial_volume: 50
  seek_step: 10
  volume_step: 2
system:
  mocp_file_path: mocp
  shutdown_command:
  - sudo
  - shutdown
  - -h
  - now
```


## Configuration File

The permanent settings are read from a YAML file:
the one given with `--configuration-file-path`, or,
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
| `buttons.origin` | `gpio` | Where the button events come from: `gpio`, `none`, or `simulator` |
| `buttons.repeat_hold_time` | `0.3` | How often the hold press of a held button repeats, in seconds |
| `display.font_file_path` | none | The TrueType font; if not set, the font built in Pillow |
| `display.show_side_icons` | `true` | Whether the icons of the buttons are shown in playback mode, when the service starts |
| `display.target` | `st7789` | Where the screen is drawn: `none`, `simulator`, or `st7789` |
| `display.tick` | `0.5` | How often the MOC status is read and the screen updated, in seconds |
| `library.directory_path` | `/music` | The music root directory |
| `playback.initial_volume` | `50` | The volume set when the service starts, between 0 and 100 |
| `playback.seek_step` | `10` | The amount of each seek, in seconds |
| `playback.volume_step` | `2` | The amount of each volume change, between 1 and 100 |
| `system.mocp_file_path` | `mocp` | The `mocp` executable |
| `system.shutdown_command` | `sudo shutdown -h now` | The command shutting down the host, as a string or as a list |

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
| `--library-directory-path` | `library.directory_path` |

An example of configuration file:

```yaml
display:
  font_file_path: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
library:
  directory_path: /home/pi/music
playback:
  initial_volume: 30
```

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
| `B_hold` | `previous` | |
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
      B_hold: null
      X_long: next
```

With the default values, holding `X` in playback mode seeks 10 seconds forward
after 0.6 seconds, and then 10 more seconds every 0.3 seconds, until `X` is released.

### Button Icons

In playback mode, a band of 20 pixels on each side of the screen
shows the icons of the actions of the buttons, next to the buttons themselves:
for each button, the icon of its short press and, below it,
the icon of its long press or, if it has none, of its hold press.

The icons follow the button map: a button without action,
or with an action that has no icon (the `menu_*` actions), shows no icon.

Set `display.show_side_icons` to `false` to hide the icons:
the two bands are then used by the playback information.
The icons can also be shown or hidden while the service runs, from the `Settings` menu.


## Menus

The top level menu has the following items:

- `Library`: browse the music root directory.
  Each directory lists `Play this folder`, its subdirectories,
  and its audio files (FLAC, MP3, OGG, and WAV).
  Selecting `Play this folder` or an audio file
  replaces the MOC playlist with it, and plays it.
- `Settings`: change the settings of the running service.
  For now, it has one item, `Side icons: on` or `Side icons: off`:
  selecting it shows or hides the icons of the buttons in playback mode.
  The change lasts until the service is stopped:
  when it starts, the service takes the value from `display.show_side_icons`.
- `Host`: show the name and the IP address of the host,
  and `Shut down`, which asks for confirmation
  before running `system.shutdown_command`.
- `Back to playback`: close the menu.
